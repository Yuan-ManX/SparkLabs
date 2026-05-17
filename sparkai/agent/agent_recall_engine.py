import uuid
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict


class RecallDomain(Enum):
    GAME_MECHANICS = "game_mechanics"
    LEVEL_DESIGN = "level_design"
    ASSETS = "assets"
    CODE_PATTERNS = "code_patterns"
    BUG_FIXES = "bug_fixes"
    PERFORMANCE_TIPS = "performance_tips"
    UI_PATTERNS = "ui_patterns"
    NARRATIVE_STRUCTURES = "narrative_structures"


class RelevanceScore(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecallStrategy(Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    TEMPORAL = "temporal"
    HYBRID = "hybrid"


@dataclass
class KnowledgeFragment:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: RecallDomain = RecallDomain.CODE_PATTERNS
    content: str = ""
    source_session_id: str = ""
    source_project: str = ""
    tags: List[str] = field(default_factory=list)
    relevance: RelevanceScore = RelevanceScore.MEDIUM
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "content": self.content,
            "source_session_id": self.source_session_id,
            "source_project": self.source_project,
            "tags": self.tags,
            "relevance": self.relevance.value,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "confidence": self.confidence,
        }


@dataclass
class RecallQuery:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    text: str = ""
    domain_filter: Optional[RecallDomain] = None
    strategy: RecallStrategy = RecallStrategy.HYBRID
    max_results: int = 10
    min_confidence: float = 0.0
    context_window: str = ""


@dataclass
class RecallResult:
    fragment: KnowledgeFragment
    score: float = 0.0
    match_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fragment": self.fragment.to_dict(),
            "score": self.score,
            "match_reason": self.match_reason,
        }


class RecallEngine:
    _instance: Optional["RecallEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._fragments: Dict[str, KnowledgeFragment] = {}
        self._domain_index: Dict[RecallDomain, Set[str]] = defaultdict(set)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._session_index: Dict[str, Set[str]] = defaultdict(set)
        self._project_index: Dict[str, Set[str]] = defaultdict(set)
        self._links: Dict[str, Set[str]] = defaultdict(set)
        self._fragment_count: int = 0
        self._query_count: int = 0
        self._access_count: int = 0
        self._transfers: List[Dict[str, Any]] = []
        self._on_ingest_callbacks: List[Callable[[KnowledgeFragment], None]] = []

    @classmethod
    def get_instance(cls) -> "RecallEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _index_fragment(self, fragment: KnowledgeFragment) -> None:
        self._domain_index[fragment.domain].add(fragment.id)
        for tag in fragment.tags:
            self._tag_index[tag].add(fragment.id)
        if fragment.source_session_id:
            self._session_index[fragment.source_session_id].add(fragment.id)
        if fragment.source_project:
            self._project_index[fragment.source_project].add(fragment.id)

    def _unindex_fragment(self, fragment: KnowledgeFragment) -> None:
        if fragment.id in self._domain_index[fragment.domain]:
            self._domain_index[fragment.domain].discard(fragment.id)
        for tag in fragment.tags:
            if fragment.id in self._tag_index[tag]:
                self._tag_index[tag].discard(fragment.id)
        if fragment.source_session_id:
            self._session_index[fragment.source_session_id].discard(fragment.id)
        if fragment.source_project:
            self._project_index[fragment.source_project].discard(fragment.id)

    def _keyword_score(self, query_text: str, fragment: KnowledgeFragment) -> float:
        if not query_text:
            return 0.0
        query_lower = query_text.lower()
        content_lower = fragment.content.lower()
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        if not query_words:
            return 0.0
        overlap = query_words & content_words
        keyword_ratio = len(overlap) / len(query_words)
        tag_hits = sum(1 for tag in fragment.tags if tag.lower() in query_lower)
        tag_bonus = min(0.3, tag_hits * 0.1)
        return min(1.0, keyword_ratio + tag_bonus)

    def _temporal_score(self, fragment: KnowledgeFragment) -> float:
        age_hours = (time.time() - fragment.created_at) / 3600.0
        if age_hours <= 0:
            return 1.0
        decay = max(0.0, 1.0 - (age_hours / 720.0))
        recency_boost = min(1.0, fragment.access_count / 50.0) * 0.3
        return min(1.0, decay + recency_boost)

    def _semantic_score(self, query_text: str, fragment: KnowledgeFragment) -> float:
        if not query_text:
            return 0.0
        query_lower = query_text.lower()
        content_lower = fragment.content.lower()
        if query_lower in content_lower:
            return 0.9
        query_terms = query_lower.split()
        if not query_terms:
            return 0.0
        term_hits = sum(1 for term in query_terms if term in content_lower)
        term_ratio = term_hits / len(query_terms)
        tag_match = 1.0 if any(tag.lower() in query_lower for tag in fragment.tags) else 0.2
        return min(1.0, (term_ratio * 0.7) + (tag_match * 0.3))

    def _compute_score(self, query: RecallQuery, fragment: KnowledgeFragment) -> Tuple[float, str]:
        reasons: List[str] = []
        score = 0.0

        if query.strategy == RecallStrategy.KEYWORD:
            score = self._keyword_score(query.text, fragment)
            reasons.append(f"keyword({score:.2f})")
        elif query.strategy == RecallStrategy.TEMPORAL:
            score = self._temporal_score(fragment)
            reasons.append(f"temporal({score:.2f})")
        elif query.strategy == RecallStrategy.SEMANTIC:
            score = self._semantic_score(query.text, fragment)
            reasons.append(f"semantic({score:.2f})")
        else:
            kw = self._keyword_score(query.text, fragment)
            tm = self._temporal_score(fragment)
            sm = self._semantic_score(query.text, fragment)
            score = (kw * 0.25) + (tm * 0.15) + (sm * 0.60)
            reasons.append(f"hybrid(kw={kw:.2f},tm={tm:.2f},sm={sm:.2f})")

        score *= fragment.confidence
        reasons.append(f"conf={fragment.confidence:.2f}")

        if fragment.relevance == RelevanceScore.CRITICAL:
            score *= 1.2
            reasons.append("critical_boost")
        elif fragment.relevance == RelevanceScore.HIGH:
            score *= 1.1
            reasons.append("high_boost")

        score = min(1.0, score)
        return score, "|".join(reasons)

    def ingest_fragment(self, fragment: KnowledgeFragment) -> str:
        with self._lock:
            self._fragments[fragment.id] = fragment
            self._index_fragment(fragment)
            self._fragment_count += 1
            for callback in self._on_ingest_callbacks:
                try:
                    callback(fragment)
                except Exception:
                    pass
            return fragment.id

    def ingest_from_session(
        self,
        fragments: List[KnowledgeFragment],
        session_id: str = "",
        project: str = "",
    ) -> List[str]:
        ingested_ids: List[str] = []
        with self._lock:
            for fragment in fragments:
                if session_id and not fragment.source_session_id:
                    fragment.source_session_id = session_id
                if project and not fragment.source_project:
                    fragment.source_project = project
                self._fragments[fragment.id] = fragment
                self._index_fragment(fragment)
                ingested_ids.append(fragment.id)
            self._fragment_count += len(ingested_ids)
            for callback in self._on_ingest_callbacks:
                for fragment in fragments:
                    try:
                        callback(fragment)
                    except Exception:
                        pass
            return ingested_ids

    def search(self, query: RecallQuery) -> List[RecallResult]:
        with self._lock:
            self._query_count += 1
            candidates = list(self._fragments.values())

            if query.domain_filter is not None:
                domain_ids = self._domain_index.get(query.domain_filter, set())
                candidates = [f for f in candidates if f.id in domain_ids]

            results: List[RecallResult] = []
            for fragment in candidates:
                if fragment.confidence < query.min_confidence:
                    continue
                score, reason = self._compute_score(query, fragment)
                if score > 0.0:
                    results.append(RecallResult(fragment=fragment, score=score, match_reason=reason))

            results.sort(key=lambda r: r.score, reverse=True)
            selected = results[: query.max_results]

            for rr in selected:
                rr.fragment.access_count += 1
                self._access_count += 1

            return selected

    def contextual_search(
        self,
        text: str,
        domain: Optional[RecallDomain] = None,
        context: str = "",
        max_results: int = 10,
    ) -> List[RecallResult]:
        query = RecallQuery(
            text=text,
            domain_filter=domain,
            strategy=RecallStrategy.HYBRID,
            max_results=max_results,
            min_confidence=0.0,
            context_window=context,
        )
        return self.search(query)

    def get_domain_fragments(
        self, domain: RecallDomain, min_confidence: float = 0.0
    ) -> List[KnowledgeFragment]:
        with self._lock:
            domain_ids = self._domain_index.get(domain, set())
            fragments = [self._fragments[fid] for fid in domain_ids if fid in self._fragments]
            fragments = [f for f in fragments if f.confidence >= min_confidence]
            fragments.sort(key=lambda f: f.created_at, reverse=True)
            return fragments

    def get_trending_topics(self, top_n: int = 10) -> List[Tuple[str, int]]:
        with self._lock:
            tag_counts: Dict[str, int] = defaultdict(int)
            for fragment in self._fragments.values():
                for tag in fragment.tags:
                    tag_counts[tag] += 1
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_tags[:top_n]

    def link_fragments(self, fragment_id_a: str, fragment_id_b: str) -> bool:
        with self._lock:
            if fragment_id_a not in self._fragments or fragment_id_b not in self._fragments:
                return False
            self._links[fragment_id_a].add(fragment_id_b)
            self._links[fragment_id_b].add(fragment_id_a)
            return True

    def transfer_to_session(
        self, fragment_ids: List[str], target_session_id: str
    ) -> List[KnowledgeFragment]:
        with self._lock:
            transferred: List[KnowledgeFragment] = []
            for fid in fragment_ids:
                if fid in self._fragments:
                    original = self._fragments[fid]
                    transferred_fragment = KnowledgeFragment(
                        domain=original.domain,
                        content=original.content,
                        source_session_id=target_session_id,
                        source_project=original.source_project,
                        tags=list(original.tags),
                        relevance=original.relevance,
                        confidence=original.confidence,
                    )
                    self._fragments[transferred_fragment.id] = transferred_fragment
                    self._index_fragment(transferred_fragment)
                    self._fragment_count += 1
                    transferred.append(transferred_fragment)
                    self._transfers.append({
                        "from_fragment_id": fid,
                        "to_fragment_id": transferred_fragment.id,
                        "target_session_id": target_session_id,
                        "timestamp": time.time(),
                    })
            return transferred

    def prune_stale(self, max_age_hours: float = 720.0, min_confidence: float = 0.1) -> int:
        with self._lock:
            now = time.time()
            stale_ids: List[str] = []
            for fragment in self._fragments.values():
                age_hours = (now - fragment.created_at) / 3600.0
                if age_hours > max_age_hours and fragment.confidence < min_confidence:
                    stale_ids.append(fragment.id)
            for fid in stale_ids:
                fragment = self._fragments.pop(fid)
                self._unindex_fragment(fragment)
                self._links.pop(fid, None)
                for linked_set in self._links.values():
                    linked_set.discard(fid)
            self._fragment_count = len(self._fragments)
            return len(stale_ids)

    def consolidate_insights(
        self,
        domain: Optional[RecallDomain] = None,
        min_confidence: float = 0.3,
        max_fragments: int = 5,
    ) -> Dict[str, Any]:
        with self._lock:
            fragments = list(self._fragments.values())
            if domain is not None:
                domain_ids = self._domain_index.get(domain, set())
                fragments = [f for f in fragments if f.id in domain_ids]
            fragments = [f for f in fragments if f.confidence >= min_confidence]
            fragments.sort(key=lambda f: (f.confidence * f.access_count), reverse=True)
            top = fragments[:max_fragments]

            domains_present: Dict[str, int] = defaultdict(int)
            tags_present: Dict[str, int] = defaultdict(int)
            total_confidence = 0.0
            for f in top:
                domains_present[f.domain.value] += 1
                for tag in f.tags:
                    tags_present[tag] += 1
                total_confidence += f.confidence

            return {
                "summary_fragments": [f.to_dict() for f in top],
                "dominant_domains": dict(domains_present),
                "common_tags": dict(
                    sorted(tags_present.items(), key=lambda x: x[1], reverse=True)[:10]
                ),
                "average_confidence": total_confidence / len(top) if top else 0.0,
                "total_considered": len(fragments),
                "consolidated_at": time.time(),
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            by_domain: Dict[str, int] = {}
            for domain, ids in self._domain_index.items():
                by_domain[domain.value] = len(ids)

            by_relevance: Dict[str, int] = defaultdict(int)
            avg_confidence = 0.0
            for fragment in self._fragments.values():
                by_relevance[fragment.relevance.value] += 1
                avg_confidence += fragment.confidence
            total = len(self._fragments)
            avg_confidence = avg_confidence / total if total > 0 else 0.0

            return {
                "total_fragments": total,
                "fragment_count": self._fragment_count,
                "query_count": self._query_count,
                "access_count": self._access_count,
                "by_domain": by_domain,
                "by_relevance": dict(by_relevance),
                "average_confidence": round(avg_confidence, 3),
                "total_links": len(self._links),
                "total_transfers": len(self._transfers),
                "unique_sessions": len(self._session_index),
                "unique_projects": len(self._project_index),
                "unique_tags": len(self._tag_index),
            }


def get_recall_engine() -> RecallEngine:
    return RecallEngine.get_instance()