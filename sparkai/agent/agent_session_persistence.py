"""
SparkLabs Agent - Session Persistence

Persistent session storage with search and retrieval.
Maintains session history across agent restarts using
a lightweight embedded store. Enables the agent to
reference past game development sessions, resume work,
and search across all historical interactions.

Architecture:
  SessionStore
    |-- SessionRecord (id, project, timestamp, summary, tags)
    |-- SessionIndex (in-memory index with full-text search)
    |-- SessionArchive (JSON-based persistent storage)
    |-- SessionSearch (keyword, tag, date-range queries)
    |-- SessionExport (individual or batch export)
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


@dataclass
class SessionRecord:
    session_id: str
    project_name: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    summary: str = ""
    message_count: int = 0
    token_total: int = 0
    tags: List[str] = field(default_factory=list)
    last_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "summary": self.summary,
            "message_count": self.message_count,
            "token_total": self.token_total,
            "tags": self.tags,
        }

    def search_text(self) -> str:
        return " ".join([
            self.session_id,
            self.project_name,
            self.summary,
            *self.tags,
            self.last_message[:200],
        ]).lower()


class SessionStore:
    """
    Persistent session storage with full-text search.

    Maintains game development session records across
    agent restarts. AI agents can recall past sessions,
    search by keywords or tags, and resume interrupted
    work. Sessions are stored as JSON in a configurable
    directory with automatic indexing.
    """

    _instance: Optional["SessionStore"] = None

    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}
        self._storage_path: str = ""
        self._index: Dict[str, set] = {}
        self._lock = threading.Lock()
        self._MAX_SESSIONS = 500
        self._dirty: bool = False

    @classmethod
    def get_instance(cls) -> "SessionStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_storage_path(self, path: str) -> None:
        self._storage_path = path
        os.makedirs(path, exist_ok=True)

    def create(
        self,
        session_id: str,
        project_name: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionRecord:
        with self._lock:
            record = SessionRecord(
                session_id=session_id,
                project_name=project_name,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._sessions[session_id] = record
            self._index_record(record)
            if len(self._sessions) > self._MAX_SESSIONS:
                oldest = min(
                    self._sessions.keys(),
                    key=lambda k: self._sessions[k].created_at,
                )
                self._remove_from_index(self._sessions[oldest])
                del self._sessions[oldest]
            self._dirty = True
            return record

    def update(
        self,
        session_id: str,
        status: Optional[SessionStatus] = None,
        summary: str = "",
        last_message: str = "",
        token_delta: int = 0,
    ) -> Optional[SessionRecord]:
        with self._lock:
            record = self._sessions.get(session_id)
            if not record:
                return None
            record.updated_at = time.time()
            record.message_count += 1
            record.token_total += token_delta
            if status:
                record.status = status
            if summary:
                record.summary = summary
            if last_message:
                record.last_message = last_message
            self._index_record(record)
            self._dirty = True
            return record

    def get(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    def search(
        self,
        query: str = "",
        tag: Optional[str] = None,
        project_name: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 20,
    ) -> List[SessionRecord]:
        q = query.lower() if query else ""
        results: List[SessionRecord] = []

        with self._lock:
            for record in self._sessions.values():
                if tag and tag not in record.tags:
                    continue
                if project_name and record.project_name != project_name:
                    continue
                if status and record.status != status:
                    continue
                if q:
                    if not self._matches_query(record, q):
                        continue
                results.append(record)

        results.sort(key=lambda r: r.updated_at, reverse=True)
        return results[:limit]

    def find_by_tag(self, tag: str) -> List[SessionRecord]:
        return self.search(tag=tag)

    def find_active(self) -> List[SessionRecord]:
        return self.search(status=SessionStatus.ACTIVE)

    def find_recent(self, limit: int = 10) -> List[SessionRecord]:
        return self.search(limit=limit)

    def save_to_disk(self) -> int:
        if not self._storage_path:
            return 0

        count = 0
        with self._lock:
            path = os.path.join(self._storage_path, "sessions.json")
            try:
                data = {
                    sid: r.to_dict() for sid, r in self._sessions.items()
                }
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                self._dirty = False
                count = len(data)
            except Exception:
                pass

        return count

    def load_from_disk(self) -> int:
        if not self._storage_path:
            return 0

        path = os.path.join(self._storage_path, "sessions.json")
        if not os.path.exists(path):
            return 0

        count = 0
        try:
            with open(path, "r") as f:
                data = json.load(f)

            with self._lock:
                for sid, d in data.items():
                    record = SessionRecord(
                        session_id=sid,
                        project_name=d.get("project_name", ""),
                        status=SessionStatus(d.get("status", "completed")),
                        created_at=d.get("created_at", 0),
                        updated_at=d.get("updated_at", 0),
                        summary=d.get("summary", ""),
                        message_count=d.get("message_count", 0),
                        token_total=d.get("token_total", 0),
                        tags=d.get("tags", []),
                        metadata=d.get("metadata", {}),
                    )
                    self._sessions[sid] = record
                    self._index_record(record)
                    count += 1
                self._dirty = False
        except Exception:
            pass

        return count

    def delete(self, session_id: str) -> bool:
        with self._lock:
            record = self._sessions.pop(session_id, None)
            if record:
                self._remove_from_index(record)
                self._dirty = True
                return True
            return False

    def _matches_query(self, record: SessionRecord, query: str) -> bool:
        text = record.search_text()
        return query in text

    def _index_record(self, record: SessionRecord) -> None:
        words = set(re.findall(r'\w+', record.search_text()))
        for word in words:
            if len(word) < 2:
                continue
            self._index.setdefault(word, set()).add(record.session_id)

    def _remove_from_index(self, record: SessionRecord) -> None:
        sid = record.session_id
        for word_set in self._index.values():
            word_set.discard(sid)

    def get_stats(self) -> dict:
        with self._lock:
            by_status: Dict[str, int] = {}
            total_tokens = 0
            for record in self._sessions.values():
                s = record.status.value
                by_status[s] = by_status.get(s, 0) + 1
                total_tokens += record.token_total

            all_tags = set()
            for record in self._sessions.values():
                all_tags.update(record.tags)

            return {
                "total_sessions": len(self._sessions),
                "by_status": by_status,
                "total_tokens": total_tokens,
                "unique_tags": len(all_tags),
                "index_entries": len(self._index),
                "storage_path": self._storage_path,
                "dirty": self._dirty,
            }

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._index.clear()
            self._dirty = False


def get_session_store() -> SessionStore:
    return SessionStore.get_instance()
