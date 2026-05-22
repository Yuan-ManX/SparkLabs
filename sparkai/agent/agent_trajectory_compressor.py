"""
Trajectory Compressor - Compress agent interaction trajectories for efficient
storage and model training data generation within SparkLabs AI game studio.

Architecture:
    TrajectoryCompressor/
    |-- CompressionMode (SUMMARIZE, PRUNE, MERGE enumeration)
    |-- TrajectoryFormat (CHATML, SHAREGPT, OPENAI enumeration)
    |-- RelevanceFilter (STRICT, MODERATE, LOOSE enumeration)
    |-- Trajectory (raw interaction sequence dataclass)
    |-- CompressedTrajectory (compressed output dataclass)
    |-- TurnSummary (single interaction turn summary dataclass)
    |-- CompressionConfig (compression parameter bundle dataclass)
    |-- TrainingExample (model training sample dataclass)
    |-- TrajectoryCompressor (global compression orchestration)

Processes agent session recordings into compact representations suitable
for long-term archival, cross-session context injection, and fine-tuning
dataset generation. Applies summarization, relevance filtering, and
multi-trajectory merging strategies.
"""

from __future__ import annotations

import uuid
import time
import json
import re
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class CompressionMode(Enum):
    SUMMARIZE = auto()
    PRUNE = auto()
    MERGE = auto()


class TrajectoryFormat(Enum):
    CHATML = auto()
    SHAREGPT = auto()
    OPENAI = auto()


class RelevanceFilter(Enum):
    STRICT = auto()
    MODERATE = auto()
    LOOSE = auto()


@dataclass
class TurnSummary:
    summary_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    turn_index: int = 0
    role: str = ""
    content_preview: str = ""
    tool_calls: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    token_count: int = 0
    relevance_score: float = 0.0
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "turn_index": self.turn_index,
            "role": self.role,
            "preview": self.content_preview[:120],
            "tool_calls": self.tool_calls,
            "decisions": self.key_decisions,
            "tokens": self.token_count,
            "relevance": round(self.relevance_score, 3),
        }


@dataclass
class Trajectory:
    trajectory_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    session_id: str = ""
    created_at: float = 0.0
    turns: List[Dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    total_tokens: int = 0
    total_tool_calls: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def estimate_tokens(self) -> int:
        total = 0
        for turn in self.turns:
            content = turn.get("content", "")
            if isinstance(content, str):
                total += len(content.split())
            tool_data = turn.get("tool_calls", [])
            if isinstance(tool_data, list):
                for tc in tool_data:
                    if isinstance(tc, dict):
                        total += len(json.dumps(tc, default=str).split())
        return total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "total_tokens": self.total_tokens,
            "tool_calls": self.total_tool_calls,
            "tags": self.tags,
            "age_seconds": round(time.time() - self.created_at, 1),
        }


@dataclass
class CompressedTrajectory:
    compressed_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_trajectory_id: str = ""
    mode: CompressionMode = CompressionMode.SUMMARIZE
    created_at: float = 0.0
    original_turn_count: int = 0
    compressed_turn_count: int = 0
    original_tokens: int = 0
    compressed_tokens: int = 0
    compression_ratio: float = 0.0
    turns: List[Dict[str, Any]] = field(default_factory=list)
    summaries: List[TurnSummary] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compressed_id": self.compressed_id,
            "source": self.source_trajectory_id,
            "mode": self.mode.name,
            "original_turns": self.original_turn_count,
            "compressed_turns": self.compressed_turn_count,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "ratio": round(self.compression_ratio, 3),
            "summaries": len(self.summaries),
        }


@dataclass
class CompressionConfig:
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: CompressionMode = CompressionMode.SUMMARIZE
    max_tokens: int = 4096
    preserve_tool_calls: bool = True
    merge_adjacent_roles: bool = True
    min_turn_confidence: float = 0.5
    summary_style: str = "concise"
    strip_redundant: bool = True
    include_metadata: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "mode": self.mode.name,
            "max_tokens": self.max_tokens,
            "preserve_tool_calls": self.preserve_tool_calls,
            "merge_adjacent": self.merge_adjacent_roles,
            "confidence": self.min_turn_confidence,
        }


@dataclass
class TrainingExample:
    example_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trajectory_id: str = ""
    format: TrajectoryFormat = TrajectoryFormat.CHATML
    created_at: float = 0.0
    messages: List[Dict[str, Any]] = field(default_factory=list)
    token_count: int = 0
    quality_score: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "example_id": self.example_id,
            "trajectory_id": self.trajectory_id,
            "format": self.format.name,
            "message_count": len(self.messages),
            "token_count": self.token_count,
            "quality": round(self.quality_score, 3),
            "tags": self.tags,
        }


class TrajectoryCompressor:
    _instance: Optional["TrajectoryCompressor"] = None
    _lock = threading.RLock()
    _MAX_TRAJECTORIES = 100
    _MAX_TURNS_PER_TRAJECTORY = 2000

    def __init__(self):
        self._trajectories: Dict[str, Trajectory] = {}
        self._compressed: Dict[str, CompressedTrajectory] = {}
        self._training_examples: Dict[str, TrainingExample] = {}
        self._configs: Dict[str, CompressionConfig] = {}
        self._total_ingested: int = 0
        self._total_compressed: int = 0
        self._total_exported: int = 0
        self._total_merged: int = 0

    @classmethod
    def get_instance(cls) -> "TrajectoryCompressor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ingest_trajectory(
        self,
        agent_id: str,
        session_id: str,
        turns: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Trajectory:
        with self._lock:
            trajectory = Trajectory(
                agent_id=agent_id,
                session_id=session_id,
                created_at=time.time(),
                turns=turns[:self._MAX_TURNS_PER_TRAJECTORY],
                turn_count=min(len(turns), self._MAX_TURNS_PER_TRAJECTORY),
                total_tool_calls=sum(
                    1 for t in turns if t.get("role") == "tool" or t.get("tool_calls")
                ),
                metadata=metadata or {},
                tags=tags or [],
            )
            trajectory.total_tokens = trajectory.estimate_tokens()

            self._trajectories[trajectory.trajectory_id] = trajectory
            self._total_ingested += 1

            if len(self._trajectories) > self._MAX_TRAJECTORIES:
                oldest_key = min(
                    self._trajectories.keys(),
                    key=lambda k: self._trajectories[k].created_at,
                )
                del self._trajectories[oldest_key]

            return trajectory

    def compress(
        self,
        trajectory_id: str,
        mode: CompressionMode = CompressionMode.SUMMARIZE,
        config: Optional[CompressionConfig] = None,
    ) -> Optional[CompressedTrajectory]:
        trajectory = self._trajectories.get(trajectory_id)
        if trajectory is None:
            return None

        cfg = config or CompressionConfig(mode=mode)
        original_tokens = trajectory.total_tokens
        original_turns = trajectory.turn_count

        compressed_turns, summaries = self._apply_compression(trajectory, cfg)
        compressed_tokens = self._estimate_compressed_tokens(compressed_turns)

        ratio = (
            (1.0 - compressed_tokens / original_tokens)
            if original_tokens > 0
            else 0.0
        )

        with self._lock:
            result = CompressedTrajectory(
                source_trajectory_id=trajectory_id,
                mode=mode,
                created_at=time.time(),
                original_turn_count=original_turns,
                compressed_turn_count=len(compressed_turns),
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=ratio,
                turns=compressed_turns,
                summaries=summaries,
                metadata={"config": cfg.to_dict()},
            )
            self._compressed[result.compressed_id] = result
            self._total_compressed += 1
            return result

    def export_training_data(
        self,
        trajectory_id: str,
        format: TrajectoryFormat = TrajectoryFormat.CHATML,
        max_tokens: int = 8192,
    ) -> Optional[TrainingExample]:
        trajectory = self._trajectories.get(trajectory_id)
        if trajectory is None:
            return None

        messages = self._convert_format(trajectory.turns, format, max_tokens)
        token_count = sum(
            len(json.dumps(m, default=str).split()) for m in messages
        )
        quality = min(1.0, len(messages) / max(1, trajectory.turn_count))

        with self._lock:
            example = TrainingExample(
                trajectory_id=trajectory_id,
                format=format,
                created_at=time.time(),
                messages=messages,
                token_count=token_count,
                quality_score=quality,
                tags=trajectory.tags,
            )
            self._training_examples[example.example_id] = example
            self._total_exported += 1
            return example

    def summarize_turn(self, turn_id: str) -> Optional[TurnSummary]:
        summary_id = f"turn_{turn_id}"
        for comp in self._compressed.values():
            for summary in comp.summaries:
                if summary.summary_id == summary_id:
                    return summary
        return None

    def filter_by_relevance(
        self,
        trajectory_id: str,
        query: str,
        filter: RelevanceFilter = RelevanceFilter.MODERATE,
    ) -> List[Dict[str, Any]]:
        trajectory = self._trajectories.get(trajectory_id)
        if trajectory is None:
            return []

        thresholds = {
            RelevanceFilter.STRICT: 0.7,
            RelevanceFilter.MODERATE: 0.4,
            RelevanceFilter.LOOSE: 0.15,
        }
        threshold = thresholds.get(filter, 0.4)
        query_lower = query.lower()

        scored_turns: List[Tuple[float, Dict[str, Any]]] = []
        for turn in trajectory.turns:
            content = turn.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            score = self._compute_relevance(content, query_lower)
            if score >= threshold:
                scored_turns.append((score, turn))

        scored_turns.sort(key=lambda x: x[0], reverse=True)
        return [turn for _, turn in scored_turns]

    def merge_trajectories(
        self,
        trajectory_ids: List[str],
    ) -> Optional[CompressedTrajectory]:
        all_turns: List[Dict[str, Any]] = []
        source_ids: List[str] = []

        for tid in trajectory_ids:
            trajectory = self._trajectories.get(tid)
            if trajectory is None:
                continue
            all_turns.extend(trajectory.turns)
            source_ids.append(tid)

        if not all_turns:
            return None

        deduplicated = self._deduplicate_turns(all_turns)
        sorted_turns = sorted(
            deduplicated,
            key=lambda t: t.get("timestamp", 0.0) if isinstance(t.get("timestamp"), (int, float)) else 0.0,
        )

        total_tokens = sum(
            len(str(t.get("content", "")).split()) for t in sorted_turns
        )
        original_total = sum(
            self._trajectories[tid].total_tokens
            for tid in source_ids if tid in self._trajectories
        )

        ratio = (1.0 - total_tokens / original_total) if original_total > 0 else 0.0

        with self._lock:
            merged_id = f"merged_{uuid.uuid4().hex[:12]}"
            result = CompressedTrajectory(
                compressed_id=merged_id,
                source_trajectory_id=",".join(source_ids),
                mode=CompressionMode.MERGE,
                created_at=time.time(),
                original_turn_count=sum(
                    self._trajectories[tid].turn_count
                    for tid in source_ids if tid in self._trajectories
                ),
                compressed_turn_count=len(sorted_turns),
                original_tokens=original_total,
                compressed_tokens=total_tokens,
                compression_ratio=ratio,
                turns=sorted_turns,
            )
            self._compressed[result.compressed_id] = result
            self._total_merged += 1
            return result

    def estimate_compression_ratio(self, trajectory_id: str) -> Optional[Dict[str, Any]]:
        trajectory = self._trajectories.get(trajectory_id)
        if trajectory is None:
            return None

        original = trajectory.total_tokens
        estimated_modes: Dict[str, float] = {}
        for mode in CompressionMode:
            cfg = CompressionConfig(mode=mode)
            compressed_turns, _ = self._apply_compression(trajectory, cfg)
            compressed = self._estimate_compressed_tokens(compressed_turns)
            ratio = (1.0 - compressed / original) if original > 0 else 0.0
            estimated_modes[mode.name] = round(ratio, 3)

        return {
            "trajectory_id": trajectory_id,
            "original_tokens": original,
            "original_turns": trajectory.turn_count,
            "estimated_ratios": estimated_modes,
        }

    def get_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        return self._trajectories.get(trajectory_id)

    def get_compressed(self, compressed_id: str) -> Optional[CompressedTrajectory]:
        return self._compressed.get(compressed_id)

    def list_trajectories(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Trajectory]:
        results = list(self._trajectories.values())
        if agent_id:
            results = [t for t in results if t.agent_id == agent_id]
        if session_id:
            results = [t for t in results if t.session_id == session_id]
        results.sort(key=lambda t: t.created_at, reverse=True)
        return results[:limit]

    def list_compressed(self, trajectory_id: Optional[str] = None) -> List[CompressedTrajectory]:
        results = list(self._compressed.values())
        if trajectory_id:
            results = [c for c in results if c.source_trajectory_id == trajectory_id]
        return sorted(results, key=lambda c: c.created_at, reverse=True)

    def delete_trajectory(self, trajectory_id: str) -> bool:
        with self._lock:
            if trajectory_id in self._trajectories:
                del self._trajectories[trajectory_id]
                to_remove = [
                    cid for cid, c in self._compressed.items()
                    if trajectory_id in c.source_trajectory_id
                ]
                for cid in to_remove:
                    del self._compressed[cid]
                return True
            return False

    def _apply_compression(
        self,
        trajectory: Trajectory,
        config: CompressionConfig,
    ) -> Tuple[List[Dict[str, Any]], List[TurnSummary]]:
        turns = trajectory.turns
        summaries: List[TurnSummary] = []

        if config.mode == CompressionMode.SUMMARIZE:
            turns = self._summarize_turns(turns, config, summaries)
        elif config.mode == CompressionMode.PRUNE:
            turns = self._prune_turns(turns, config)
        elif config.mode == CompressionMode.MERGE:
            turns = self._merge_consecutive_turns(turns, config)

        if config.strip_redundant:
            turns = self._strip_redundant_content(turns)

        return turns, summaries

    def _summarize_turns(
        self,
        turns: List[Dict[str, Any]],
        config: CompressionConfig,
        summaries_out: List[TurnSummary],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for i, turn in enumerate(turns):
            content = turn.get("content", "")
            content_str = str(content) if not isinstance(content, str) else content

            if len(content_str) > 500 and i % 3 != 0:
                preview = content_str[:300] + "..."
                summary = TurnSummary(
                    turn_index=i,
                    role=str(turn.get("role", "")),
                    content_preview=preview,
                    tool_calls=self._extract_tool_names(turn),
                    key_decisions=self._extract_decisions(content_str),
                    token_count=len(content_str.split()),
                    relevance_score=0.75,
                    created_at=time.time(),
                )
                summaries_out.append(summary)
                result.append({
                    "role": turn.get("role", "user"),
                    "content": preview,
                    "summary": summary.to_dict(),
                })
            else:
                result.append(turn)

        return result

    def _prune_turns(
        self,
        turns: List[Dict[str, Any]],
        config: CompressionConfig,
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for i, turn in enumerate(turns):
            content = turn.get("content", "")
            content_str = str(content) if not isinstance(content, str) else content

            if not content_str.strip():
                continue

            if len(content_str) < 20 and not turn.get("tool_calls"):
                continue

            tool_names = turn.get("tool_calls") or turn.get("function_call")
            if not config.preserve_tool_calls and not tool_names:
                if len(turns) > 100 and i % 3 != 0:
                    continue

            result.append(turn)

        return result

    def _merge_consecutive_turns(
        self,
        turns: List[Dict[str, Any]],
        config: CompressionConfig,
    ) -> List[Dict[str, Any]]:
        if not config.merge_adjacent_roles or not turns:
            return list(turns)

        result: List[Dict[str, Any]] = [dict(turns[0])]
        for turn in turns[1:]:
            prev = result[-1]
            if (
                prev.get("role") == turn.get("role")
                and prev.get("role") in ("user", "assistant")
                and not prev.get("tool_calls")
                and not turn.get("tool_calls")
            ):
                prev_content = str(prev.get("content", ""))
                turn_content = str(turn.get("content", ""))
                prev["content"] = prev_content + "\n\n" + turn_content
            else:
                result.append(dict(turn))

        return result

    def _strip_redundant_content(self, turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        patterns = [
            r'^(okay|sure|got it|understood)[.,!]*$',
            r'^let me (know|see|check|think)[.,!]*$',
        ]
        result: List[Dict[str, Any]] = []
        for turn in turns:
            content = str(turn.get("content", "")).strip().lower()
            should_skip = any(
                re.match(p, content) for p in patterns
            )
            if not should_skip or turn.get("tool_calls"):
                result.append(turn)
        return result

    def _estimate_compressed_tokens(self, turns: List[Dict[str, Any]]) -> int:
        total = 0
        for turn in turns:
            content = turn.get("content", "")
            total += len(str(content).split())
            if turn.get("tool_calls"):
                total += 20
        return total

    def _compute_relevance(self, content: str, query: str) -> float:
        content_lower = content.lower()
        if query in content_lower:
            return 0.5 + 0.5 * (content_lower.count(query) / max(1, len(content_lower.split()) / 10))

        query_words = set(query.split())
        content_words = set(content_lower.split())
        overlap = query_words & content_words
        if not overlap:
            return 0.0

        return 0.1 + 0.4 * (len(overlap) / len(query_words))

    def _extract_tool_names(self, turn: Dict[str, Any]) -> List[str]:
        names: List[str] = []
        tool_calls = turn.get("tool_calls", [])
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if isinstance(tc, dict):
                    name = tc.get("function", {}).get("name", "") if isinstance(tc.get("function"), dict) else tc.get("name", "")
                    if name:
                        names.append(name)
        return names

    def _extract_decisions(self, content: str) -> List[str]:
        indicators = [
            "decided to", "chose to", "will use", "going to create",
            "should implement", "recommend using", "let's build",
        ]
        decisions: List[str] = []
        content_lower = content.lower()
        for indicator in indicators:
            idx = content_lower.find(indicator)
            if idx >= 0:
                snippet = content[idx:idx + 200].strip()
                decisions.append(snippet.split(".")[0] if "." in snippet else snippet[:120])
        return decisions[:3]

    def _convert_format(
        self,
        turns: List[Dict[str, Any]],
        format: TrajectoryFormat,
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        if format == TrajectoryFormat.CHATML:
            return self._to_chatml(turns, max_tokens)
        elif format == TrajectoryFormat.SHAREGPT:
            return self._to_sharegpt(turns, max_tokens)
        elif format == TrajectoryFormat.OPENAI:
            return self._to_openai(turns, max_tokens)
        return list(turns[:max_tokens])

    def _to_chatml(
        self,
        turns: List[Dict[str, Any]],
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        token_count = 0
        messages: List[Dict[str, Any]] = []
        for turn in turns:
            role = turn.get("role", "user")
            content = str(turn.get("content", ""))
            msg = {"role": role, "content": content}
            msg_tokens = len(content.split())
            if token_count + msg_tokens > max_tokens and messages:
                break
            messages.append(msg)
            token_count += msg_tokens
        return messages

    def _to_sharegpt(
        self,
        turns: List[Dict[str, Any]],
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        messages = self._to_chatml(turns, max_tokens)
        return [{"conversations": [
            {"from": "human" if m["role"] == "user" else "gpt", "value": m["content"]}
            for m in messages
        ]}]

    def _to_openai(
        self,
        turns: List[Dict[str, Any]],
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        return self._to_chatml(turns, max_tokens)

    def _deduplicate_turns(self, turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set = set()
        result: List[Dict[str, Any]] = []
        for turn in turns:
            content = str(turn.get("content", ""))
            role = str(turn.get("role", ""))
            key = f"{role}:{content[:100]}"
            if key not in seen:
                seen.add(key)
                result.append(turn)
        return result

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_original_tokens = sum(
                t.total_tokens for t in self._trajectories.values()
            )
            total_compressed_tokens = sum(
                c.compressed_tokens for c in self._compressed.values()
            )
            total_training = sum(
                e.token_count for e in self._training_examples.values()
            )

            by_mode: Dict[str, int] = {}
            for c in self._compressed.values():
                by_mode[c.mode.name] = by_mode.get(c.mode.name, 0) + 1

            by_format: Dict[str, int] = {}
            for e in self._training_examples.values():
                by_format[e.format.name] = by_format.get(e.format.name, 0) + 1

            return {
                "total_trajectories": len(self._trajectories),
                "total_compressed": len(self._compressed),
                "total_training_examples": len(self._training_examples),
                "total_ingested": self._total_ingested,
                "total_exported": self._total_exported,
                "total_merged": self._total_merged,
                "original_tokens": total_original_tokens,
                "compressed_tokens": total_compressed_tokens,
                "training_tokens": total_training,
                "by_compression_mode": by_mode,
                "by_export_format": by_format,
                "trajectories": [
                    t.to_dict() for t in list(self._trajectories.values())[:20]
                ],
            }


def get_trajectory_compressor() -> TrajectoryCompressor:
    return TrajectoryCompressor.get_instance()