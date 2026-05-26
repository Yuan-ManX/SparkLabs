"""
Trajectory Generator - Records agent decision-making trajectories for
training future AI models within SparkLabs AI game studio.

Architecture:
    TrajectoryGenerator/
    |-- TrajectoryTurn (single interaction turn dataclass)
    |-- TrajectorySession (full decision-making session dataclass)
    |-- CompressedTrajectory (compressed trajectory output dataclass)
    |-- TrajectoryBatch (bundled trajectory collection dataclass)
    |-- TrajectoryGenerator (global generation orchestration)

Captures the full sequence of observations, thoughts, tool calls, and
results from agent decision-making sessions. Compresses trajectories by
removing redundant turns using an auxiliary summary model, preserving
the essential decision-making structure for efficient storage and
downstream model training.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TrajectoryFormat(Enum):
    OPENAI_MESSAGES = "openai_messages"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    LANGCHAIN_TRACES = "langchain_traces"
    SPARKAI_INTERNAL = "sparkai_internal"
    HUGGINGFACE_DATASET = "huggingface_dataset"


class CompressionStrategy(Enum):
    NONE = "none"
    SUMMARIZE_MIDDLE = "summarize_middle"
    KEEP_HEAD_TAIL = "keep_head_tail"
    TOOL_ONLY = "tool_only"
    SEMANTIC_DEDUP = "semantic_dedup"


class TurnRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    OBSERVATION = "observation"
    REFLECTION = "reflection"


class QualityLabel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TrajectoryTurn:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    turn_index: int = 0
    role: TurnRole = TurnRole.ASSISTANT
    content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = 0.0
    token_count: int = 0
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "turn_index": self.turn_index,
            "role": self.role.value,
            "content": self.content[:500] if len(self.content) > 500 else self.content,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "timestamp": self.timestamp,
            "token_count": self.token_count,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class TrajectorySession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_name: str = ""
    task_description: str = ""
    turns: List[TrajectoryTurn] = field(default_factory=list)
    quality: QualityLabel = QualityLabel.ACCEPTABLE
    start_time: float = 0.0
    end_time: Optional[float] = None
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    _turn_counter: int = 0

    def add_turn(self, turn: TrajectoryTurn) -> None:
        self._turn_counter += 1
        turn.turn_index = self._turn_counter
        turn.session_id = self.id
        self.turns.append(turn)
        self.total_tokens += turn.token_count
        self.total_latency_ms += turn.latency_ms

    def get_duration(self) -> float:
        end = self.end_time or _time_module.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "task_description": self.task_description[:200],
            "turn_count": len(self.turns),
            "quality": self.quality.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.get_duration(), 1),
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "metadata": self.metadata,
        }


@dataclass
class CompressedTrajectory:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_session_id: str = ""
    strategy: CompressionStrategy = CompressionStrategy.NONE
    original_turns: int = 0
    compressed_turns: int = 0
    compression_ratio: float = 0.0
    head_turns_kept: int = 0
    tail_turns_kept: int = 0
    summary: str = ""
    turns: List[TrajectoryTurn] = field(default_factory=list)
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_session_id": self.source_session_id,
            "strategy": self.strategy.value,
            "original_turns": self.original_turns,
            "compressed_turns": self.compressed_turns,
            "compression_ratio": round(self.compression_ratio, 3),
            "head_turns_kept": self.head_turns_kept,
            "tail_turns_kept": self.tail_turns_kept,
            "summary": self.summary[:300] if len(self.summary) > 300 else self.summary,
        }


@dataclass
class TrajectoryBatch:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    sessions: List[str] = field(default_factory=list)
    format: TrajectoryFormat = TrajectoryFormat.SPARKAI_INTERNAL
    created_at: float = 0.0
    total_sessions: int = 0
    total_turns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "session_count": len(self.sessions),
            "format": self.format.value,
            "created_at": self.created_at,
            "total_sessions": self.total_sessions,
            "total_turns": self.total_turns,
        }


# ---------------------------------------------------------------------------
# TrajectoryGenerator
# ---------------------------------------------------------------------------


class TrajectoryGenerator:
    _instance: Optional["TrajectoryGenerator"] = None
    _lock = threading.RLock()
    _MAX_SESSIONS = 200
    _MAX_TURNS_PER_SESSION = 5000
    _MAX_BATCHES = 100

    def __init__(self):
        self._sessions: Dict[str, TrajectorySession] = {}
        self._compressed: Dict[str, CompressedTrajectory] = {}
        self._batches: Dict[str, TrajectoryBatch] = {}
        self._total_turns_recorded: int = 0
        self._total_sessions_created: int = 0
        self._total_sessions_completed: int = 0
        self._total_compressions: int = 0
        self._total_exports: int = 0

    @classmethod
    def get_instance(cls) -> "TrajectoryGenerator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(
        self,
        agent_name: str = "",
        task_description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrajectorySession:
        with self._lock:
            session = TrajectorySession(
                agent_name=agent_name,
                task_description=task_description,
                start_time=_time_module.time(),
                metadata=metadata or {},
            )
            self._sessions[session.id] = session
            self._total_sessions_created += 1

            if len(self._sessions) > self._MAX_SESSIONS:
                oldest = min(
                    self._sessions.keys(),
                    key=lambda k: self._sessions[k].start_time,
                )
                del self._sessions[oldest]

            return session

    def end_session(
        self,
        session_id: str = "",
        quality: QualityLabel = QualityLabel.ACCEPTABLE,
    ) -> Optional[TrajectorySession]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        with self._lock:
            session.end_time = _time_module.time()
            session.quality = quality
            self._total_sessions_completed += 1

        return session

    # ------------------------------------------------------------------
    # Turn recording
    # ------------------------------------------------------------------

    def record_turn(
        self,
        session_id: str = "",
        role: TurnRole = TurnRole.ASSISTANT,
        content: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        token_count: int = 0,
        latency_ms: float = 0.0,
    ) -> Optional[TrajectoryTurn]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if len(session.turns) >= self._MAX_TURNS_PER_SESSION:
            return None

        turn = TrajectoryTurn(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
            timestamp=_time_module.time(),
            token_count=token_count,
            latency_ms=latency_ms,
        )

        with self._lock:
            session.add_turn(turn)
            self._total_turns_recorded += 1

        return turn

    # ------------------------------------------------------------------
    # Compression
    # ------------------------------------------------------------------

    def compress_trajectory(
        self,
        session_id: str = "",
        strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE_MIDDLE,
        head_turns: int = 5,
        tail_turns: int = 5,
    ) -> Optional[CompressedTrajectory]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        original_count = len(session.turns)
        if original_count == 0:
            return None

        compressed_turn_list, summary, kept_head, kept_tail = self._apply_compression(
            session.turns, strategy, head_turns, tail_turns
        )

        compressed_count = len(compressed_turn_list)
        ratio = (
            (1.0 - compressed_count / original_count)
            if original_count > 0
            else 0.0
        )

        with self._lock:
            result = CompressedTrajectory(
                source_session_id=session_id,
                strategy=strategy,
                original_turns=original_count,
                compressed_turns=compressed_count,
                compression_ratio=ratio,
                head_turns_kept=kept_head,
                tail_turns_kept=kept_tail,
                summary=summary,
                turns=compressed_turn_list,
                created_at=_time_module.time(),
            )
            self._compressed[result.id] = result
            self._total_compressions += 1

        return result

    def _apply_compression(
        self,
        turns: List[TrajectoryTurn],
        strategy: CompressionStrategy,
        head_turns: int,
        tail_turns: int,
    ) -> Tuple[List[TrajectoryTurn], str, int, int]:
        turn_count = len(turns)

        if strategy == CompressionStrategy.NONE:
            return list(turns), "", turn_count, 0

        if strategy == CompressionStrategy.SUMMARIZE_MIDDLE:
            return self._compress_summarize_middle(turns, head_turns, tail_turns)

        if strategy == CompressionStrategy.KEEP_HEAD_TAIL:
            return self._compress_keep_head_tail(turns, head_turns, tail_turns)

        if strategy == CompressionStrategy.TOOL_ONLY:
            return self._compress_tool_only(turns)

        if strategy == CompressionStrategy.SEMANTIC_DEDUP:
            return self._compress_semantic_dedup(turns, head_turns, tail_turns)

        return list(turns), "", turn_count, 0

    def _compress_summarize_middle(
        self,
        turns: List[TrajectoryTurn],
        head_turns: int,
        tail_turns: int,
    ) -> Tuple[List[TrajectoryTurn], str, int, int]:
        total = len(turns)

        if total <= head_turns + tail_turns:
            return list(turns), "", total, 0

        head = turns[:head_turns]
        tail = turns[-tail_turns:] if tail_turns > 0 else []
        middle = turns[head_turns:total - tail_turns] if tail_turns > 0 else turns[head_turns:]

        summary_parts: List[str] = []
        for turn in middle:
            role_str = turn.role.value
            content_preview = turn.content[:100] if turn.content else ""
            if content_preview:
                summary_parts.append(f"[{role_str}] {content_preview}")

        summary = " | ".join(summary_parts[:20])
        if len(summary_parts) > 20:
            summary += f" ... (+{len(summary_parts) - 20} more turns)"

        result = list(head) + list(tail)
        return result, summary, len(head), len(tail)

    def _compress_keep_head_tail(
        self,
        turns: List[TrajectoryTurn],
        head_turns: int,
        tail_turns: int,
    ) -> Tuple[List[TrajectoryTurn], str, int, int]:
        total = len(turns)

        if total <= head_turns + tail_turns:
            return list(turns), "", total, 0

        head = turns[:head_turns]
        tail = turns[-tail_turns:] if tail_turns > 0 else []

        summary = f"Middle {total - head_turns - tail_turns} turns removed."
        return list(head) + list(tail), summary, len(head), len(tail)

    def _compress_tool_only(
        self,
        turns: List[TrajectoryTurn],
    ) -> Tuple[List[TrajectoryTurn], str, int, int]:
        kept: List[TrajectoryTurn] = []
        for turn in turns:
            if turn.role in (TurnRole.TOOL, TurnRole.OBSERVATION):
                kept.append(turn)
                continue
            if turn.tool_calls:
                kept.append(turn)
                continue
            if turn.role == TurnRole.SYSTEM:
                kept.append(turn)
                continue

        summary = f"Kept {len(kept)} out of {len(turns)} tool-relevant turns."
        return kept, summary, 0, 0

    def _compress_semantic_dedup(
        self,
        turns: List[TrajectoryTurn],
        head_turns: int,
        tail_turns: int,
    ) -> Tuple[List[TrajectoryTurn], str, int, int]:
        total = len(turns)

        if total <= head_turns + tail_turns:
            return list(turns), "", total, 0

        head = turns[:head_turns]
        tail = turns[-tail_turns:] if tail_turns > 0 else []
        middle = turns[head_turns:total - tail_turns] if tail_turns > 0 else turns[head_turns:]

        seen: Dict[str, bool] = {}
        deduplicated: List[TrajectoryTurn] = []
        duplicates_removed = 0

        for turn in middle:
            key = self._build_semantic_key(turn)
            if key in seen:
                duplicates_removed += 1
                continue
            seen[key] = True
            deduplicated.append(turn)

        summary = f"Deduplicated {duplicates_removed} semantically similar turns."
        result = list(head) + deduplicated + list(tail)
        return result, summary, len(head), len(tail)

    def _build_semantic_key(self, turn: TrajectoryTurn) -> str:
        role = turn.role.value
        content_sig = turn.content[:80].strip().lower() if turn.content else ""
        tool_sig = ""
        if turn.tool_calls:
            tool_names = sorted(
                tc.get("name", "") for tc in turn.tool_calls if isinstance(tc, dict)
            )
            tool_sig = ",".join(tool_names)
        return f"{role}:{content_sig}:{tool_sig}"

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_trajectory(
        self,
        session_id: str = "",
        format: TrajectoryFormat = TrajectoryFormat.SPARKAI_INTERNAL,
    ) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if format == TrajectoryFormat.OPENAI_MESSAGES:
            return self._export_openai_messages(session)
        elif format == TrajectoryFormat.ANTHROPIC_MESSAGES:
            return self._export_anthropic_messages(session)
        elif format == TrajectoryFormat.LANGCHAIN_TRACES:
            return self._export_langchain_traces(session)
        elif format == TrajectoryFormat.SPARKAI_INTERNAL:
            return self._export_sparkai_internal(session)
        elif format == TrajectoryFormat.HUGGINGFACE_DATASET:
            return self._export_huggingface_dataset(session)

        return self._export_sparkai_internal(session)

    def _export_openai_messages(self, session: TrajectorySession) -> Dict[str, Any]:
        messages: List[Dict[str, Any]] = []
        for turn in session.turns:
            msg: Dict[str, Any] = {"role": turn.role.value, "content": turn.content}
            if turn.tool_calls:
                msg["tool_calls"] = turn.tool_calls
            messages.append(msg)

        return {
            "format": "openai_messages",
            "session_id": session.id,
            "messages": messages,
        }

    def _export_anthropic_messages(self, session: TrajectorySession) -> Dict[str, Any]:
        messages: List[Dict[str, Any]] = []
        for turn in session.turns:
            role_map = {
                TurnRole.USER: "user",
                TurnRole.ASSISTANT: "assistant",
            }
            mapped_role = role_map.get(turn.role, turn.role.value)
            msg: Dict[str, Any] = {"role": mapped_role, "content": [{"type": "text", "text": turn.content}]}
            messages.append(msg)

        return {
            "format": "anthropic_messages",
            "session_id": session.id,
            "messages": messages,
        }

    def _export_langchain_traces(self, session: TrajectorySession) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        for turn in session.turns:
            steps.append({
                "step": turn.turn_index,
                "action": turn.role.value,
                "observation": turn.content[:500],
                "timestamp": turn.timestamp,
            })

        return {
            "format": "langchain_traces",
            "session_id": session.id,
            "trace": steps,
        }

    def _export_sparkai_internal(self, session: TrajectorySession) -> Dict[str, Any]:
        return {
            "format": "sparkai_internal",
            "session": session.to_dict(),
            "turns": [t.to_dict() for t in session.turns],
        }

    def _export_huggingface_dataset(self, session: TrajectorySession) -> Dict[str, Any]:
        conversations: List[Dict[str, Any]] = []
        current_messages: List[Dict[str, str]] = []

        for turn in session.turns:
            current_messages.append({"role": turn.role.value, "content": turn.content})

        conversations.append({"messages": current_messages})

        return {
            "format": "huggingface_dataset",
            "session_id": session.id,
            "conversations": conversations,
        }

    # ------------------------------------------------------------------
    # Batching
    # ------------------------------------------------------------------

    def create_batch(
        self,
        name: str = "",
        session_ids: Optional[List[str]] = None,
        format: TrajectoryFormat = TrajectoryFormat.SPARKAI_INTERNAL,
    ) -> Optional[TrajectoryBatch]:
        if not session_ids:
            return None

        valid_sessions: List[str] = []
        total_turns = 0

        for sid in session_ids:
            session = self._sessions.get(sid)
            if session is None:
                continue
            valid_sessions.append(sid)
            total_turns += len(session.turns)

        if not valid_sessions:
            return None

        with self._lock:
            batch = TrajectoryBatch(
                name=name,
                sessions=valid_sessions,
                format=format,
                created_at=_time_module.time(),
                total_sessions=len(valid_sessions),
                total_turns=total_turns,
            )
            self._batches[batch.id] = batch

            if len(self._batches) > self._MAX_BATCHES:
                oldest_batch = min(
                    self._batches.keys(),
                    key=lambda k: self._batches[k].created_at,
                )
                del self._batches[oldest_batch]

        return batch

    def export_batch(
        self,
        batch_id: str = "",
        output_path: str = "",
    ) -> bool:
        batch = self._batches.get(batch_id)
        if batch is None:
            return False

        export_data: Dict[str, Any] = {
            "batch": batch.to_dict(),
            "sessions": [],
        }

        for sid in batch.sessions:
            exported = self.export_trajectory(sid, batch.format)
            if exported:
                export_data["sessions"].append(exported)

        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
            self._total_exports += 1
            return True
        except (OSError, TypeError):
            return False

    # ------------------------------------------------------------------
    # Quality and labeling
    # ------------------------------------------------------------------

    def get_session_quality(self, session_id: str = "") -> Optional[QualityLabel]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return session.quality

    def label_session(
        self,
        session_id: str = "",
        quality: QualityLabel = QualityLabel.ACCEPTABLE,
        notes: str = "",
    ) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False

        with self._lock:
            session.quality = quality
            if notes:
                session.metadata["quality_notes"] = notes

        return True

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def compute_statistics(self, session_id: str = "") -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        turns = session.turns
        turn_count = len(turns)

        roles: Dict[str, int] = {}
        tool_call_count = 0
        total_content_length = 0

        for turn in turns:
            role_key = turn.role.value
            roles[role_key] = roles.get(role_key, 0) + 1
            tool_call_count += len(turn.tool_calls)
            total_content_length += len(turn.content)

        avg_content_length = total_content_length / max(turn_count, 1)
        avg_tokens_per_turn = session.total_tokens / max(turn_count, 1)
        avg_latency_per_turn = session.total_latency_ms / max(turn_count, 1)

        return {
            "session_id": session_id,
            "agent_name": session.agent_name,
            "task_description": session.task_description[:200],
            "quality": session.quality.value,
            "turn_count": turn_count,
            "total_tokens": session.total_tokens,
            "total_latency_ms": round(session.total_latency_ms, 2),
            "duration_seconds": round(session.get_duration(), 1),
            "avg_tokens_per_turn": round(avg_tokens_per_turn, 1),
            "avg_latency_per_turn_ms": round(avg_latency_per_turn, 2),
            "avg_content_length": round(avg_content_length, 1),
            "tool_call_count": tool_call_count,
            "role_distribution": roles,
        }

    def filter_sessions(
        self,
        min_quality: Optional[QualityLabel] = None,
        min_turns: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> List[TrajectorySession]:
        quality_order = {
            QualityLabel.EXCELLENT: 5,
            QualityLabel.GOOD: 4,
            QualityLabel.ACCEPTABLE: 3,
            QualityLabel.POOR: 2,
            QualityLabel.FAILED: 1,
        }

        results: List[TrajectorySession] = []

        for session in self._sessions.values():
            if min_quality is not None:
                current_level = quality_order.get(session.quality, 0)
                min_level = quality_order.get(min_quality, 0)
                if current_level < min_level:
                    continue

            if min_turns is not None:
                if len(session.turns) < min_turns:
                    continue

            if max_tokens is not None:
                if session.total_tokens > max_tokens:
                    continue

            results.append(session)

        results.sort(key=lambda s: s.start_time, reverse=True)
        return results

    def get_generator_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_turns = sum(len(s.turns) for s in self._sessions.values())
            total_tokens = sum(s.total_tokens for s in self._sessions.values())
            total_latency = sum(s.total_latency_ms for s in self._sessions.values())

            quality_counts: Dict[str, int] = {}
            for session in self._sessions.values():
                q = session.quality.value
                quality_counts[q] = quality_counts.get(q, 0) + 1

            strategy_counts: Dict[str, int] = {}
            for comp in self._compressed.values():
                s = comp.strategy.value
                strategy_counts[s] = strategy_counts.get(s, 0) + 1

            active_count = sum(
                1 for s in self._sessions.values() if s.end_time is None
            )

            return {
                "total_sessions_created": self._total_sessions_created,
                "total_sessions_completed": self._total_sessions_completed,
                "active_sessions": active_count,
                "total_turns_recorded": self._total_turns_recorded,
                "total_turns_in_memory": total_turns,
                "total_tokens": total_tokens,
                "total_latency_ms": round(total_latency, 2),
                "total_compressions": self._total_compressions,
                "total_exports": self._total_exports,
                "total_batches": len(self._batches),
                "quality_distribution": quality_counts,
                "compression_strategies": strategy_counts,
                "max_sessions": self._MAX_SESSIONS,
            }

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_session(self, session_id: str = "") -> Optional[TrajectorySession]:
        return self._sessions.get(session_id)

    def get_compressed(self, compressed_id: str = "") -> Optional[CompressedTrajectory]:
        return self._compressed.get(compressed_id)

    def get_batch(self, batch_id: str = "") -> Optional[TrajectoryBatch]:
        return self._batches.get(batch_id)

    def list_sessions(
        self,
        agent_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[TrajectorySession]:
        results = list(self._sessions.values())
        if agent_name:
            results = [s for s in results if s.agent_name == agent_name]
        results.sort(key=lambda s: s.start_time, reverse=True)
        return results[:limit]

    def list_compressed(self, session_id: str = "") -> List[CompressedTrajectory]:
        results = list(self._compressed.values())
        if session_id:
            results = [c for c in results if c.source_session_id == session_id]
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results

    def list_batches(self) -> List[TrajectoryBatch]:
        return sorted(self._batches.values(), key=lambda b: b.created_at, reverse=True)

    def delete_session(self, session_id: str = "") -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                to_remove_compressed = [
                    cid for cid, c in self._compressed.items()
                    if c.source_session_id == session_id
                ]
                for cid in to_remove_compressed:
                    del self._compressed[cid]
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "total_turns": self._total_turns_recorded,
            "compressed_count": len(self._compressed),
            "export_count": self._total_exports,
        }


# ---------------------------------------------------------------------------
# Module accessor
# ---------------------------------------------------------------------------


def get_trajectory_generator() -> TrajectoryGenerator:
    return TrajectoryGenerator.get_instance()