"""
Session Search - Semantic and keyword search across agent sessions.

Architecture:
    SessionSearch/
    |-- SearchIndex (in-memory inverted index)
    |-- SearchQuery (structured query parameters)
    |-- SearchResult (ranked result with metadata)
    |-- SessionSearch (unified session search engine)

Enables full-text and structured search across agent conversation
sessions, with time-range filtering, relevance scoring, and result pagination.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class SearchScope(Enum):
    ALL = auto()
    TITLE = auto()
    MESSAGES = auto()
    TOOL_CALLS = auto()
    SYSTEM_PROMPTS = auto()


@dataclass
class SearchQuery:
    text: str
    scope: SearchScope = SearchScope.ALL
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    max_results: int = 20
    min_relevance: float = 0.0
    case_sensitive: bool = False


@dataclass
class SearchResult:
    session_id: str
    content_preview: str
    relevance: float
    timestamp: float
    source_field: str = "messages"
    match_context: str = ""
    agent_id: str = ""
    session_title: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "content_preview": self.content_preview[:300],
            "relevance": round(self.relevance, 4),
            "timestamp": self.timestamp,
            "source_field": self.source_field,
            "match_context": self.match_context[:200],
            "agent_id": self.agent_id,
            "session_title": self.session_title,
        }


class SearchIndex:
    """In-memory inverted search index."""

    def __init__(self):
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self._total_indexed = 0

    def add(self, session_id: str, data: Dict[str, Any]) -> None:
        text = self._flatten_for_index(data)
        tokens = self._tokenize(text)

        self._documents[session_id] = data
        for token in tokens:
            self._inverted_index[token].add(session_id)

        self._total_indexed += 1

    def remove(self, session_id: str) -> bool:
        if session_id in self._documents:
            text = self._flatten_for_index(self._documents[session_id])
            tokens = self._tokenize(text)
            for token in tokens:
                self._inverted_index[token].discard(session_id)
            del self._documents[session_id]
            return True
        return False

    def search(self, query_text: str, max_results: int = 20) -> List[Tuple[str, float]]:
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)
        for token in query_tokens:
            matching_sessions = self._inverted_index.get(token, set())
            for sid in matching_sessions:
                scores[sid] += 1.0 / len(query_tokens)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:max_results]

    def get_document(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._documents.get(session_id)

    def _flatten_for_index(self, data: Dict[str, Any]) -> str:
        parts = []
        for key in ["title", "messages", "tool_calls", "system_prompt", "description"]:
            value = data.get(key, "")
            if isinstance(value, list):
                parts.append(" ".join(str(v) for v in value))
            elif value:
                parts.append(str(value))
        return " ".join(parts)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r'[a-zA-Z0-9_]{2,}', text)
        stop_words = {"the","is","at","which","on","and","a","an","in","to","of","for",
                      "with","be","by","that","this","it","or","as","we","he","she","they",
                      "are","was","has","had","not","but","from","can","will","have","do"}
        return [t for t in tokens if t not in stop_words]

    @property
    def document_count(self) -> int:
        return len(self._documents)

    def clear(self) -> None:
        self._documents.clear()
        self._inverted_index.clear()
        self._total_indexed = 0


class SessionSearch:
    """Unified session search engine with relevance ranking."""

    _instance: Optional["SessionSearch"] = None

    def __init__(self):
        self._index = SearchIndex()
        self._total_queries = 0
        self._total_indexed = 0

    @classmethod
    def get_instance(cls) -> "SessionSearch":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def index_session(self, session_id: str, title: str = "",
                      messages: Optional[List[str]] = None,
                      agent_id: str = "",
                      timestamp: Optional[float] = None,
                      extra_data: Optional[Dict[str, Any]] = None) -> None:
        data = {
            "title": title,
            "messages": messages or [],
            "agent_id": agent_id,
            "timestamp": timestamp or time.time(),
            **(extra_data or {}),
        }
        self._index.add(session_id, data)
        self._total_indexed += 1

    def remove_session(self, session_id: str) -> bool:
        return self._index.remove(session_id)

    def search(self, query: SearchQuery) -> List[SearchResult]:
        self._total_queries += 1

        text = query.text if query.case_sensitive else query.text.lower()
        ranked = self._index.search(text, max_results=query.max_results)

        results: List[SearchResult] = []
        for session_id, relevance in ranked:
            if relevance < query.min_relevance:
                continue

            doc = self._index.get_document(session_id)
            if not doc:
                continue

            if query.session_id and session_id != query.session_id:
                continue
            if query.agent_id and doc.get("agent_id") != query.agent_id:
                continue

            ts = doc.get("timestamp", 0)
            if query.start_time and ts < query.start_time:
                continue
            if query.end_time and ts > query.end_time:
                continue

            content = self._get_scoped_content(doc, query.scope)
            match_ctx = self._extract_match_context(content, text)

            results.append(SearchResult(
                session_id=session_id,
                content_preview=content[:300],
                relevance=relevance,
                timestamp=ts,
                source_field=query.scope.name.lower(),
                match_context=match_ctx,
                agent_id=doc.get("agent_id", ""),
                session_title=doc.get("title", ""),
            ))

        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:query.max_results]

    def quick_search(self, query_text: str, max_results: int = 10) -> List[Dict[str, Any]]:
        q = SearchQuery(text=query_text, max_results=max_results)
        return [r.to_dict() for r in self.search(q)]

    def _get_scoped_content(self, doc: Dict[str, Any], scope: SearchScope) -> str:
        if scope == SearchScope.TITLE:
            return doc.get("title", "")
        elif scope == SearchScope.MESSAGES:
            msgs = doc.get("messages", [])
            return "\n".join(msgs) if isinstance(msgs, list) else str(msgs)
        elif scope == SearchScope.TOOL_CALLS:
            return str(doc.get("tool_calls", ""))
        elif scope == SearchScope.SYSTEM_PROMPTS:
            return doc.get("system_prompt", "")
        else:
            return self._flatten_all(doc)

    def _flatten_all(self, doc: Dict[str, Any]) -> str:
        parts = [doc.get("title", "")]
        msgs = doc.get("messages", [])
        if isinstance(msgs, list):
            parts.extend(msgs[:50])
        return "\n".join(parts)

    def _extract_match_context(self, content: str, query: str) -> str:
        if not query or query not in content.lower():
            return ""
        idx = content.lower().find(query.lower())
        start = max(0, idx - 60)
        end = min(len(content), idx + len(query) + 60)
        ctx = content[start:end]
        return f"...{ctx}..."

    def list_indexed_sessions(self) -> List[Dict[str, Any]]:
        results = []
        for sid in list(self._index._documents.keys())[:100]:
            doc = self._index.get_document(sid)
            if doc:
                results.append({
                    "session_id": sid,
                    "title": doc.get("title", ""),
                    "agent_id": doc.get("agent_id", ""),
                    "timestamp": doc.get("timestamp", 0),
                })
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_queries": self._total_queries,
            "total_indexed": self._total_indexed,
            "index_size": self._index.document_count,
            "unique_tokens": len(self._index._inverted_index),
        }

    def rebuild_index(self) -> int:
        docs = dict(self._index._documents)
        self._index.clear()
        for sid, data in docs.items():
            self._index.add(sid, data)
        return self._index.document_count

    def clear(self) -> None:
        self._index.clear()
        self._total_indexed = 0
        self._total_queries = 0


def get_session_search() -> SessionSearch:
    return SessionSearch.get_instance()
