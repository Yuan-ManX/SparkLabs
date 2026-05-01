"""
SparkAI Agent - Session Compaction Engine

Manages agent session context windows with automatic compaction,
session persistence, forking, and health probing. When context
approaches token limits, the engine compresses older messages
while preserving recent context and verifying session integrity.

Architecture:
  SessionCompactionEngine
    |-- CompactionStrategy (pluggable compression)
    |-- SessionStore (persistence layer)
    |-- HealthProbe (post-compaction integrity verification)
    |-- SessionFork (branching for parallel exploration)

Compaction Flow:
  1. Monitor token usage across active sessions
  2. When threshold exceeded, select compaction strategy
  3. Compress older messages into summary
  4. Inject continuation message for seamless context
  5. Run health probe to verify session integrity
  6. Persist compacted session to disk
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class CompactionStrategy(Enum):
    TAIL_PRESERVE = "tail_preserve"
    HEAD_TAIL_PRESERVE = "head_tail_preserve"
    RELEVANCE_RANKED = "relevance_ranked"
    LAYERED_SUMMARY = "layered_summary"


class SessionHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COMPACTED = "compacted"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"


class ForkStatus(Enum):
    ACTIVE = "active"
    MERGED = "merged"
    ABANDONED = "abandoned"


@dataclass
class SessionMessage:
    role: str = ""
    content: str = ""
    token_count: int = 0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "token_count": self.token_count,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class CompactionRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    strategy: CompactionStrategy = CompactionStrategy.TAIL_PRESERVE
    messages_before: int = 0
    messages_after: int = 0
    tokens_before: int = 0
    tokens_after: int = 0
    summary: str = ""
    preserved_head_count: int = 0
    preserved_tail_count: int = 0
    health_after: SessionHealth = SessionHealth.UNKNOWN
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "strategy": self.strategy.value,
            "messages_before": self.messages_before,
            "messages_after": self.messages_after,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "summary": self.summary[:500],
            "preserved_head_count": self.preserved_head_count,
            "preserved_tail_count": self.preserved_tail_count,
            "health_after": self.health_after.value,
            "created_at": self.created_at,
        }


@dataclass
class SessionFork:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_session_id: str = ""
    branch_name: str = ""
    messages: List[SessionMessage] = field(default_factory=list)
    total_tokens: int = 0
    status: ForkStatus = ForkStatus.ACTIVE
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_session_id": self.parent_session_id,
            "branch_name": self.branch_name,
            "message_count": len(self.messages),
            "total_tokens": self.total_tokens,
            "status": self.status.value,
            "created_at": self.created_at,
        }


@dataclass
class CompactableSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    messages: List[SessionMessage] = field(default_factory=list)
    total_tokens: int = 0
    max_tokens: int = 100000
    compaction_threshold: float = 0.8
    health: SessionHealth = SessionHealth.HEALTHY
    compaction_count: int = 0
    fork_parent: Optional[str] = None
    fork_name: str = ""
    workspace_root: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "message_count": len(self.messages),
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "compaction_threshold": self.compaction_threshold,
            "health": self.health.value,
            "compaction_count": self.compaction_count,
            "fork_parent": self.fork_parent,
            "fork_name": self.fork_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def needs_compaction(self) -> bool:
        return self.total_tokens >= int(self.max_tokens * self.compaction_threshold)

    def add_message(self, role: str, content: str, token_count: int = 0) -> SessionMessage:
        msg = SessionMessage(role=role, content=content, token_count=token_count or len(content.split()))
        self.messages.append(msg)
        self.total_tokens += msg.token_count
        self.updated_at = time.time()
        return msg


class SessionStore:
    """
    File-based session persistence with JSONL format and rotation.
    Each session is stored as a JSONL file for append-friendly writes.
    """

    def __init__(self, store_dir: str = ".sparkai/sessions"):
        self._store_dir = Path(store_dir)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._max_file_size = 256 * 1024
        self._max_rotations = 3

    def persist(self, session: CompactableSession) -> bool:
        try:
            file_path = self._store_dir / f"{session.id}.jsonl"
            if file_path.exists() and file_path.stat().st_size > self._max_file_size:
                self._rotate(file_path)
            with open(file_path, "a") as f:
                record = {
                    "timestamp": time.time(),
                    "session_id": session.id,
                    "agent_id": session.agent_id,
                    "total_tokens": session.total_tokens,
                    "health": session.health.value,
                    "message_count": len(session.messages),
                }
                f.write(json.dumps(record) + "\n")
            return True
        except Exception:
            return False

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._store_dir / f"{session_id}.jsonl"
        if not file_path.exists():
            return None
        try:
            last_record = None
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_record = json.loads(line)
            return last_record
        except Exception:
            return None

    def _rotate(self, file_path: Path) -> None:
        for i in range(self._max_rotations - 1, 0, -1):
            rotated = Path(f"{file_path}.{i}")
            older = Path(f"{file_path}.{i - 1}") if i > 1 else file_path
            if older.exists():
                rotated.write_text(older.read_text())
        with open(file_path, "w") as f:
            pass


class HealthProbe:
    """
    Verifies session integrity after compaction by running
    a non-destructive probe that checks message continuity
    and context coherence.
    """

    def __init__(self):
        self._probe_results: Dict[str, SessionHealth] = {}

    async def probe(self, session: CompactableSession) -> SessionHealth:
        if not session.messages:
            return SessionHealth.DEGRADED

        last_msg = session.messages[-1]
        if last_msg.role not in ("user", "assistant", "system"):
            return SessionHealth.DEGRADED

        has_system = any(m.role == "system" for m in session.messages)
        has_user = any(m.role == "user" for m in session.messages)

        if not has_user:
            return SessionHealth.DEGRADED

        if session.compaction_count > 0 and not has_system:
            return SessionHealth.COMPACTED

        health = SessionHealth.HEALTHY
        self._probe_results[session.id] = health
        session.health = health
        return health

    def get_last_result(self, session_id: str) -> Optional[SessionHealth]:
        return self._probe_results.get(session_id)


class SessionCompactionEngine:
    """
    Unified session compaction engine that manages context windows,
    persists sessions, and ensures integrity through health probes.

    The engine monitors all active sessions and automatically compacts
    them when they approach their token limits. Compaction preserves
    recent context while summarizing older messages.

    Usage:
        engine = SessionCompactionEngine()
        session = engine.create_session(agent_id="agent_1")
        engine.add_message(session.id, "user", "Hello")
        await engine.maybe_compact(session.id)
    """

    def __init__(self, default_max_tokens: int = 100000, compaction_threshold: float = 0.8):
        self._sessions: Dict[str, CompactableSession] = {}
        self._forks: Dict[str, SessionFork] = {}
        self._compaction_history: List[CompactionRecord] = []
        self._store = SessionStore()
        self._health_probe = HealthProbe()
        self._default_max_tokens = default_max_tokens
        self._default_threshold = compaction_threshold
        self._default_tail_preserve = 4
        self._default_head_preserve = 1

    def create_session(
        self,
        agent_id: str = "",
        max_tokens: Optional[int] = None,
        compaction_threshold: Optional[float] = None,
        workspace_root: Optional[str] = None,
    ) -> CompactableSession:
        session = CompactableSession(
            agent_id=agent_id,
            max_tokens=max_tokens or self._default_max_tokens,
            compaction_threshold=compaction_threshold or self._default_threshold,
            workspace_root=workspace_root,
        )
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[CompactableSession]:
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str, token_count: int = 0) -> Optional[SessionMessage]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        msg = session.add_message(role, content, token_count)
        if session.needs_compaction():
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.maybe_compact(session_id))
                else:
                    loop.run_until_complete(self.maybe_compact(session_id))
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning("Compaction scheduling failed for session %s", session_id)
        return msg

    async def maybe_compact(self, session_id: str, strategy: Optional[CompactionStrategy] = None) -> Optional[CompactionRecord]:
        session = self._sessions.get(session_id)
        if not session or not session.needs_compaction():
            return None
        return await self.compact(session_id, strategy or CompactionStrategy.HEAD_TAIL_PRESERVE)

    async def compact(self, session_id: str, strategy: CompactionStrategy = CompactionStrategy.HEAD_TAIL_PRESERVE) -> Optional[CompactionRecord]:
        session = self._sessions.get(session_id)
        if not session:
            return None

        tokens_before = session.total_tokens
        messages_before = len(session.messages)

        if strategy == CompactionStrategy.TAIL_PRESERVE:
            preserved, summary = self._compact_tail_preserve(session)
        elif strategy == CompactionStrategy.HEAD_TAIL_PRESERVE:
            preserved, summary = self._compact_head_tail_preserve(session)
        elif strategy == CompactionStrategy.RELEVANCE_RANKED:
            preserved, summary = self._compact_relevance_ranked(session)
        else:
            preserved, summary = self._compact_layered_summary(session)

        continuation = SessionMessage(
            role="system",
            content=f"[Context Continuation] Previous conversation has been summarized. Continue without acknowledging this message.\n\nSummary of prior context:\n{summary}",
            token_count=len(summary.split()),
        )

        session.messages = preserved + [continuation]
        session.total_tokens = sum(m.token_count for m in session.messages)
        session.compaction_count += 1
        session.updated_at = time.time()

        health = await self._health_probe.probe(session)

        record = CompactionRecord(
            session_id=session_id,
            strategy=strategy,
            messages_before=messages_before,
            messages_after=len(session.messages),
            tokens_before=tokens_before,
            tokens_after=session.total_tokens,
            summary=summary[:1000],
            preserved_head_count=1 if strategy in (CompactionStrategy.HEAD_TAIL_PRESERVE, CompactionStrategy.LAYERED_SUMMARY) else 0,
            preserved_tail_count=self._default_tail_preserve,
            health_after=health,
        )
        self._compaction_history.append(record)
        self._store.persist(session)

        return record

    def _compact_tail_preserve(self, session: CompactableSession) -> Tuple[List[SessionMessage], str]:
        tail_count = self._default_tail_preserve
        if len(session.messages) <= tail_count:
            return session.messages, ""

        to_summarize = session.messages[:-tail_count]
        preserved = session.messages[-tail_count:]
        summary = self._generate_summary(to_summarize)
        return preserved, summary

    def _compact_head_tail_preserve(self, session: CompactableSession) -> Tuple[List[SessionMessage], str]:
        head_count = self._default_head_preserve
        tail_count = self._default_tail_preserve

        if len(session.messages) <= head_count + tail_count:
            return session.messages, ""

        head = session.messages[:head_count]
        tail = session.messages[-tail_count:]
        middle = session.messages[head_count:-tail_count]
        summary = self._generate_summary(middle)
        return head + tail, summary

    def _compact_relevance_ranked(self, session: CompactableSession) -> Tuple[List[SessionMessage], str]:
        if len(session.messages) <= 6:
            return session.messages, ""

        scored = []
        for i, msg in enumerate(session.messages):
            score = 0.0
            recency = i / len(session.messages)
            score += recency * 0.5
            if msg.role == "system":
                score += 0.3
            if msg.role == "assistant" and msg.token_count > 50:
                score += 0.2
            scored.append((score, i, msg))

        scored.sort(key=lambda x: x[0], reverse=True)
        keep_indices = sorted([idx for _, idx, _ in scored[:8]])
        preserved = [session.messages[i] for i in keep_indices]
        summarized = [session.messages[i] for i in range(len(session.messages)) if i not in keep_indices]
        summary = self._generate_summary(summarized)
        return preserved, summary

    def _compact_layered_summary(self, session: CompactableSession) -> Tuple[List[SessionMessage], str]:
        head_count = self._default_head_preserve
        tail_count = self._default_tail_preserve

        if len(session.messages) <= head_count + tail_count + 4:
            return session.messages, ""

        head = session.messages[:head_count]
        tail = session.messages[-tail_count:]
        middle = session.messages[head_count:-tail_count]

        chunk_size = max(4, len(middle) // 3)
        chunks = [middle[i:i + chunk_size] for i in range(0, len(middle), chunk_size)]
        chunk_summaries = []
        for chunk in chunks:
            chunk_summaries.append(self._generate_summary(chunk))

        layered = " | ".join(f"[Segment {i+1}]: {s}" for i, s in enumerate(chunk_summaries))
        return head + tail, layered

    def _generate_summary(self, messages: List[SessionMessage]) -> str:
        if not messages:
            return ""

        resolved = []
        pending = []
        for msg in messages:
            content = msg.content[:200]
            if msg.role == "assistant" and ("yes" in content.lower() or "no" in content.lower() or "done" in content.lower()):
                resolved.append(content[:100])
            else:
                pending.append(content[:100])

        parts = []
        if resolved:
            parts.append(f"Resolved: {'; '.join(resolved[:3])}")
        if pending:
            parts.append(f"Pending: {'; '.join(pending[:3])}")
        parts.append(f"Messages compressed: {len(messages)}")

        return " | ".join(parts)

    def fork_session(self, session_id: str, branch_name: str = "") -> Optional[SessionFork]:
        session = self._sessions.get(session_id)
        if not session:
            return None

        fork = SessionFork(
            parent_session_id=session_id,
            branch_name=branch_name or f"fork-{uuid.uuid4().hex[:8]}",
            messages=list(session.messages),
            total_tokens=session.total_tokens,
        )
        self._forks[fork.id] = fork
        return fork

    def merge_fork(self, fork_id: str) -> bool:
        fork = self._forks.get(fork_id)
        if not fork or fork.status != ForkStatus.ACTIVE:
            return False

        session = self._sessions.get(fork.parent_session_id)
        if not session:
            return False

        session.messages = fork.messages
        session.total_tokens = fork.total_tokens
        session.updated_at = time.time()
        fork.status = ForkStatus.MERGED
        return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values()]

    def list_forks(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        forks = self._forks.values()
        if session_id:
            forks = [f for f in forks if f.parent_session_id == session_id]
        return [f.to_dict() for f in forks]

    def get_compaction_history(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        records = self._compaction_history
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        return [r.to_dict() for r in records[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total_sessions = len(self._sessions)
        total_forks = len(self._forks)
        active_forks = sum(1 for f in self._forks.values() if f.status == ForkStatus.ACTIVE)
        total_compactions = len(self._compaction_history)
        avg_compression = 0.0
        if total_compactions > 0:
            ratios = []
            for r in self._compaction_history:
                if r.tokens_before > 0:
                    ratios.append(r.tokens_after / r.tokens_before)
            avg_compression = sum(ratios) / len(ratios) if ratios else 0.0

        return {
            "total_sessions": total_sessions,
            "total_forks": total_forks,
            "active_forks": active_forks,
            "total_compactions": total_compactions,
            "avg_compression_ratio": round(avg_compression, 3),
            "healthy_sessions": sum(1 for s in self._sessions.values() if s.health == SessionHealth.HEALTHY),
        }


_global_compaction_engine: Optional[SessionCompactionEngine] = None


def get_compaction_engine() -> SessionCompactionEngine:
    global _global_compaction_engine
    if _global_compaction_engine is None:
        _global_compaction_engine = SessionCompactionEngine()
    return _global_compaction_engine
