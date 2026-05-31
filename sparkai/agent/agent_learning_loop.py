"""
SparkLabs Agent - Learning Loop

A self-improving agent learning loop system implementing the
closed learning loop (Discover -> Execute -> Learn -> Remember). The
agent observes its own execution, extracts patterns and insights, and
consolidates learnings into persistent memory to continuously elevate
its capability across sessions.

Architecture:
  LearningLoop (singleton)
    |-- LoopSession (discovery-plan-execute-evaluate-learn-remember cycle)
    |-- LearningEntry (captured insight from loop execution)
    |-- LoopPhase (state machine phases)
    |-- InsightType (categorization of discovered insights)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class LoopPhase(Enum):
    """Phases of the closed learning loop state machine."""
    DISCOVER = "discover"
    PLAN = "plan"
    EXECUTE = "execute"
    EVALUATE = "evaluate"
    LEARN = "learn"
    REMEMBER = "remember"
    COMPLETE = "complete"


class InsightType(Enum):
    """Categories of insights extracted during the learning loop."""
    PATTERN = "pattern"
    OPTIMIZATION = "optimization"
    WARNING = "warning"
    CORRECTION = "correction"
    INNOVATION = "innovation"


# ------------------------------------------------------------------
# Phase transition map
# ------------------------------------------------------------------

_PHASE_TRANSITIONS: Dict[LoopPhase, LoopPhase] = {
    LoopPhase.DISCOVER: LoopPhase.PLAN,
    LoopPhase.PLAN: LoopPhase.EXECUTE,
    LoopPhase.EXECUTE: LoopPhase.EVALUATE,
    LoopPhase.EVALUATE: LoopPhase.LEARN,
    LoopPhase.LEARN: LoopPhase.REMEMBER,
    LoopPhase.REMEMBER: LoopPhase.COMPLETE,
}

_PHASE_ORDER: Dict[LoopPhase, int] = {
    LoopPhase.DISCOVER: 0,
    LoopPhase.PLAN: 1,
    LoopPhase.EXECUTE: 2,
    LoopPhase.EVALUATE: 3,
    LoopPhase.LEARN: 4,
    LoopPhase.REMEMBER: 5,
    LoopPhase.COMPLETE: 6,
}


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

MAX_LOOP_HISTORY: int = 128
MIN_CONFIDENCE_FOR_INSIGHT: float = 0.3
INSIGHT_CONSOLIDATION_THRESHOLD: int = 3
MIN_SAMPLES_FOR_PATTERN: int = 5
SCORE_DECAY_RATE: float = 0.02
AUTO_IMPROVE_INTERVAL_SECONDS: float = 3600.0
MAX_LEARNINGS_PER_SESSION: int = 50


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class LoopSession:
    """A single pass through the closed learning loop.

    Tracks the full lifecycle from discovery through completion,
    capturing the query context, execution artifacts, extracted
    learnings, and final quality metrics.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    phase: LoopPhase = LoopPhase.DISCOVER
    query: str = ""
    plan_steps: List[str] = field(default_factory=list)
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    memory_updates: List[str] = field(default_factory=list)
    success: bool = False
    score: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    completed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase.value,
            "query": self.query,
            "plan_steps": list(self.plan_steps),
            "execution_results": [
                dict(r) for r in self.execution_results
            ],
            "learnings": list(self.learnings),
            "memory_updates": list(self.memory_updates),
            "success": self.success,
            "score": round(self.score, 3),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_seconds": round(
                (self.completed_at or _time_module.time()) - self.created_at, 2
            ),
        }


@dataclass
class LearningEntry:
    """A discrete insight captured during the learning phase.

    Each entry ties back to a session, carries a typed insight with
    a confidence score, and tracks whether it has been applied in
    subsequent improvement cycles.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    insight_type: InsightType = InsightType.PATTERN
    content: str = ""
    confidence: float = 0.5
    applied: bool = False
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "insight_type": self.insight_type.value,
            "content": self.content,
            "confidence": round(self.confidence, 3),
            "applied": self.applied,
            "timestamp": self.timestamp,
        }


# ------------------------------------------------------------------
# Clickable Code Reference: see LearningLoop class definition below
# ------------------------------------------------------------------


class LearningLoop:
    """Singleton self-improving agent learning loop.

    Orchestrates a continuous Discover -> Plan -> Execute -> Evaluate ->
    Learn -> Remember cycle. Each loop session captures execution context,
    extracts insights via pattern analysis, and consolidates learnings
    into persistent memory for cross-session improvement.
    """

    _instance: Optional[LearningLoop] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> LearningLoop:
        """Thread-safe singleton construction with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> LearningLoop:
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._sessions: Dict[str, LoopSession] = {}
        self._entries: Dict[str, LearningEntry] = {}
        self._session_index: Dict[str, List[str]] = {}
        self._insight_type_index: Dict[InsightType, List[str]] = {}
        self._consolidated_memory: List[Dict[str, Any]] = []
        self._improvement_count: int = 0
        self._last_auto_improve: float = 0.0

    # ------------------------------------------------------------------
    # Loop Lifecycle
    # ------------------------------------------------------------------

    def start_loop(self, query: str = "") -> LoopSession:
        """Begin a new learning cycle with the given query context.

        Creates a fresh LoopSession in the DISCOVER phase and returns
        it for the caller to drive through subsequent phases.
        """
        session = LoopSession(query=query, phase=LoopPhase.DISCOVER)
        with self._lock:
            self._sessions[session.id] = session
            self._session_index.setdefault(session.id, [])
        return session

    def advance_phase(
        self, session_id: str, state: Optional[Dict[str, Any]] = None
    ) -> Optional[LoopPhase]:
        """Move the session to the next phase in the learning loop.

        Accepts optional state data to attach to the session as it
        transitions (e.g., plan_steps in PLAN, execution_results in
        EXECUTE). Returns the new phase or None if the session is
        already COMPLETE or doesn't exist.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        with self._lock:
            if session.phase == LoopPhase.COMPLETE:
                return LoopPhase.COMPLETE

            previous_phase = session.phase
            next_phase = _PHASE_TRANSITIONS.get(session.phase, LoopPhase.COMPLETE)
            session.phase = next_phase

            if state:
                self._apply_phase_state(session, next_phase, state)

            if next_phase == LoopPhase.COMPLETE:
                session.completed_at = _time_module.time()

            return next_phase

    # ------------------------------------------------------------------
    # Insight Capture
    # ------------------------------------------------------------------

    def record_learning(
        self,
        session_id: str,
        insight_type: InsightType,
        content: str,
        confidence: float = 0.5,
    ) -> Optional[LearningEntry]:
        """Capture an insight from a loop session's execution phase.

        Learning entries are indexed by session and insight type for
        efficient retrieval during pattern generation. Insights below
        the minimum confidence threshold are still stored but may be
        filtered during consolidation.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        clamped_confidence = max(0.0, min(1.0, confidence))

        entry = LearningEntry(
            session_id=session_id,
            insight_type=insight_type,
            content=content,
            confidence=clamped_confidence,
        )

        with self._lock:
            self._entries[entry.id] = entry
            self._session_index.setdefault(session_id, []).append(entry.id)
            self._insight_type_index.setdefault(insight_type, []).append(entry.id)

            session.learnings.append(content)

            if len(session.learnings) > MAX_LEARNINGS_PER_SESSION:
                session.learnings = session.learnings[-MAX_LEARNINGS_PER_SESSION:]

        return entry

    # ------------------------------------------------------------------
    # Pattern Analysis
    # ------------------------------------------------------------------

    def generate_insights(
        self, min_samples: int = MIN_SAMPLES_FOR_PATTERN
    ) -> List[LearningEntry]:
        """Analyze past loop sessions to discover cross-session patterns.

        Groups learning entries by insight type and applies statistical
        clustering to surface recurring patterns, recurring warnings,
        and optimization opportunities. Generates new synthetic entries
        for high-confidence pattern clusters.
        """
        generated: List[LearningEntry] = []

        for insight_type in InsightType:
            entry_ids = self._insight_type_index.get(insight_type, [])
            if len(entry_ids) < min_samples:
                continue

            type_entries = [
                self._entries[eid] for eid in entry_ids if eid in self._entries
            ]

            clusters = self._cluster_by_similarity(type_entries)
            for cluster in clusters:
                if len(cluster) < min_samples:
                    continue

                avg_confidence = sum(e.confidence for e in cluster) / len(cluster)
                if avg_confidence < MIN_CONFIDENCE_FOR_INSIGHT:
                    continue

                representative = self._synthesize_cluster_content(cluster, insight_type)
                if not representative:
                    continue

                virtual_session_id = f"pattern_{uuid.uuid4().hex[:8]}"
                entry = LearningEntry(
                    session_id=virtual_session_id,
                    insight_type=insight_type,
                    content=representative,
                    confidence=avg_confidence,
                )
                self._entries[entry.id] = entry
                self._insight_type_index.setdefault(insight_type, []).append(entry.id)
                generated.append(entry)

        return generated

    # ------------------------------------------------------------------
    # Memory Consolidation
    # ------------------------------------------------------------------

    def consolidate_memory(self) -> List[Dict[str, Any]]:
        """Push learnings from completed sessions into persistent memory.

        Aggregates high-confidence insights across sessions, deduplicates
        redundant entries, and produces structured memory records that
        persist across loop cycles. Each consolidated memory record
        includes source traceability and a stability score.
        """
        completed_sessions = {
            sid: s for sid, s in self._sessions.items()
            if s.phase == LoopPhase.COMPLETE
        }

        candidate_entries: List[LearningEntry] = []
        for sid in completed_sessions:
            entry_ids = self._session_index.get(sid, [])
            for eid in entry_ids:
                entry = self._entries.get(eid)
                if entry is not None and not entry.applied:
                    candidate_entries.append(entry)

        consolidated: List[Dict[str, Any]] = []
        seen_signatures: set = set()

        for entry in sorted(candidate_entries, key=lambda e: e.confidence, reverse=True):
            if entry.confidence < MIN_CONFIDENCE_FOR_INSIGHT:
                continue

            sig = self._compute_content_signature(entry.content)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)

            entry.applied = True

            sources = self._trace_entry_sources(entry)
            memory_record = {
                "id": f"mem_{uuid.uuid4().hex[:12]}",
                "insight_type": entry.insight_type.value,
                "content": entry.content,
                "confidence": round(entry.confidence, 3),
                "source_session_ids": sources,
                "source_count": len(sources),
                "consolidated_at": _time_module.time(),
                "stability": self._compute_stability(entry, sources),
            }
            consolidated.append(memory_record)

        self._consolidated_memory.extend(consolidated)

        if len(self._consolidated_memory) > MAX_LOOP_HISTORY:
            self._consolidated_memory = self._consolidated_memory[-MAX_LOOP_HISTORY:]

        return consolidated

    # ------------------------------------------------------------------
    # Auto-Improvement
    # ------------------------------------------------------------------

    def auto_improve(self) -> Dict[str, Any]:
        """Trigger a full self-improvement cycle automatically.

        Runs insight generation followed by memory consolidation. Tracks
        the improvement count and enforces a cooldown interval to avoid
        excessive churn. Returns a summary of what was improved.
        """
        now = _time_module.time()
        if now - self._last_auto_improve < AUTO_IMPROVE_INTERVAL_SECONDS:
            return {
                "triggered": False,
                "reason": "cooldown_active",
                "seconds_remaining": round(
                    AUTO_IMPROVE_INTERVAL_SECONDS - (now - self._last_auto_improve), 1
                ),
            }

        with self._lock:
            self._last_auto_improve = now
            self._improvement_count += 1

            new_insights = self.generate_insights()
            consolidated = self.consolidate_memory()

            completed_sessions = sum(
                1 for s in self._sessions.values()
                if s.phase == LoopPhase.COMPLETE
            )

            avg_score = 0.0
            scored_sessions = [
                s for s in self._sessions.values()
                if s.phase == LoopPhase.COMPLETE and s.score > 0
            ]
            if scored_sessions:
                avg_score = sum(s.score for s in scored_sessions) / len(scored_sessions)

            return {
                "triggered": True,
                "improvement_round": self._improvement_count,
                "new_insights": len(new_insights),
                "consolidated_memories": len(consolidated),
                "total_memories": len(self._consolidated_memory),
                "sessions_analyzed": completed_sessions,
                "average_session_score": round(avg_score, 3),
                "timestamp": now,
            }

    # ------------------------------------------------------------------
    # Stats & Reporting
    # ------------------------------------------------------------------

    def get_loop_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics about the learning loop state.

        Includes session phase distribution, insight type breakdown,
        confidence trends, memory growth, and improvement milestones.
        """
        phase_counts: Dict[str, int] = {}
        for session in self._sessions.values():
            key = session.phase.value
            phase_counts[key] = phase_counts.get(key, 0) + 1

        insight_type_counts: Dict[str, int] = {}
        type_confidence_sums: Dict[str, float] = {}
        for entry in self._entries.values():
            key = entry.insight_type.value
            insight_type_counts[key] = insight_type_counts.get(key, 0) + 1
            type_confidence_sums[key] = type_confidence_sums.get(key, 0.0) + entry.confidence

        insight_confidence_avg: Dict[str, float] = {}
        for key, total in insight_type_counts.items():
            if total > 0:
                insight_confidence_avg[key] = round(
                    type_confidence_sums.get(key, 0.0) / total, 3
                )

        completed = [
            s for s in self._sessions.values() if s.phase == LoopPhase.COMPLETE
        ]
        successful = [s for s in completed if s.success]
        success_rate = (
            round(len(successful) / len(completed), 3) if completed else 0.0
        )

        scores = [s.score for s in completed if s.score > 0]
        avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
        min_score = round(min(scores), 3) if scores else 0.0
        max_score = round(max(scores), 3) if scores else 0.0

        durations = [
            s.completed_at - s.created_at
            for s in completed
            if s.completed_at > s.created_at
        ]
        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

        applied_count = sum(1 for e in self._entries.values() if e.applied)
        total_insights = len(self._entries)

        memory_type_breakdown: Dict[str, int] = {}
        for mem in self._consolidated_memory:
            itype = mem.get("insight_type", "unknown")
            memory_type_breakdown[itype] = memory_type_breakdown.get(itype, 0) + 1

        recent_sessions = sorted(
            [s for s in completed],
            key=lambda s: s.completed_at,
            reverse=True,
        )[:10]

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": phase_counts.get("complete", 0)
            - len(completed)
            + len(self._sessions)
            - len(completed),
            "completed_sessions": len(completed),
            "phase_distribution": phase_counts,
            "success_rate": success_rate,
            "score_summary": {
                "average": avg_score,
                "minimum": min_score,
                "maximum": max_score,
            },
            "average_duration_seconds": avg_duration,
            "total_insights": total_insights,
            "insights_applied": applied_count,
            "insights_pending": total_insights - applied_count,
            "insights_by_type": insight_type_counts,
            "insight_confidence_by_type": insight_confidence_avg,
            "consolidated_memories": len(self._consolidated_memory),
            "memory_by_type": memory_type_breakdown,
            "improvement_rounds": self._improvement_count,
            "recent_sessions": [
                {
                    "id": s.id,
                    "query": s.query[:80] if s.query else "",
                    "score": round(s.score, 3),
                    "success": s.success,
                    "learnings_count": len(s.learnings),
                }
                for s in recent_sessions
            ],
        }

    # ------------------------------------------------------------------
    # Session Lookup
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[LoopSession]:
        """Retrieve a loop session by its identifier."""
        return self._sessions.get(session_id)

    def get_session_entries(self, session_id: str) -> List[LearningEntry]:
        """Retrieve all learning entries associated with a session."""
        entry_ids = self._session_index.get(session_id, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def get_consolidated_memory(self) -> List[Dict[str, Any]]:
        """Retrieve the full persistent memory store."""
        return list(self._consolidated_memory)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_phase_state(
        session: LoopSession, phase: LoopPhase, state: Dict[str, Any]
    ) -> None:
        """Attach contextual data to a session based on the target phase."""
        if phase == LoopPhase.PLAN:
            steps = state.get("plan_steps", [])
            if isinstance(steps, list):
                session.plan_steps = steps
        elif phase == LoopPhase.EXECUTE:
            results = state.get("execution_results", [])
            if isinstance(results, list):
                session.execution_results = [
                    dict(r) if isinstance(r, dict) else {"value": r}
                    for r in results
                ]
            success = state.get("success")
            if isinstance(success, bool):
                session.success = success
        elif phase == LoopPhase.EVALUATE:
            score = state.get("score")
            if isinstance(score, (int, float)):
                session.score = float(score)
        elif phase == LoopPhase.REMEMBER:
            updates = state.get("memory_updates", [])
            if isinstance(updates, list):
                session.memory_updates = updates

    @staticmethod
    def _cluster_by_similarity(
        entries: List[LearningEntry],
    ) -> List[List[LearningEntry]]:
        """Group entries into clusters using content-based similarity.

        Uses a simplified token overlap metric to avoid external
        dependencies while still producing meaningful clusters.
        """
        if len(entries) <= 1:
            return [entries] if entries else []

        clusters: List[List[LearningEntry]] = [[entries[0]]]

        for entry in entries[1:]:
            matched = False
            entry_tokens = set(entry.content.lower().split())
            if not entry_tokens:
                clusters.append([entry])
                continue

            for cluster in clusters:
                cluster_tokens = set()
                for ce in cluster:
                    cluster_tokens.update(ce.content.lower().split())

                if not cluster_tokens:
                    continue

                overlap = len(entry_tokens & cluster_tokens) / max(
                    len(entry_tokens | cluster_tokens), 1
                )
                if overlap > 0.3:
                    cluster.append(entry)
                    matched = True
                    break

            if not matched:
                clusters.append([entry])

        return clusters

    @staticmethod
    def _synthesize_cluster_content(
        cluster: List[LearningEntry], insight_type: InsightType
    ) -> str:
        """Generate a representative summary for a cluster of insights."""
        if not cluster:
            return ""

        highest = max(cluster, key=lambda e: e.confidence)
        prefix_map = {
            InsightType.PATTERN: "Recurring pattern detected",
            InsightType.OPTIMIZATION: "Optimization opportunity identified",
            InsightType.WARNING: "Warning pattern observed",
            InsightType.CORRECTION: "Correction needed",
            InsightType.INNOVATION: "Innovation discovered",
        }
        prefix = prefix_map.get(insight_type, "Insight")
        return f"[{prefix}] across {len(cluster)} sessions: {highest.content[:180]}"

    @staticmethod
    def _compute_content_signature(content: str) -> int:
        """Produce a stable hash signature for content deduplication."""
        normalized = " ".join(content.lower().split())
        return hash(normalized)

    def _trace_entry_sources(self, entry: LearningEntry) -> List[str]:
        """Find all session IDs that contributed to this entry's context."""
        sources: List[str] = [entry.session_id]
        for eid, other in self._entries.items():
            if (
                other.insight_type == entry.insight_type
                and other.content == entry.content
                and other.session_id not in sources
            ):
                sources.append(other.session_id)
        return sources

    @staticmethod
    def _compute_stability(
        entry: LearningEntry, sources: List[str]
    ) -> float:
        """Compute a stability score based on source breadth and confidence.

        Higher stability means the insight is corroborated across more
        sessions and carries strong confidence.
        """
        base = entry.confidence
        breadth = min(len(sources), 10) / 10.0
        recency = 1.0 - min(
            (_time_module.time() - entry.timestamp) / (86400.0 * 30), 1.0
        )
        stability = base * 0.5 + breadth * 0.3 + recency * 0.2
        return round(stability, 3)

    def reset(self) -> None:
        """Clear all learning loop state. Intended for testing only."""
        with self._lock:
            self._sessions.clear()
            self._entries.clear()
            self._session_index.clear()
            self._insight_type_index.clear()
            self._consolidated_memory.clear()
            self._improvement_count = 0
            self._last_auto_improve = 0.0

    # ------------------------------------------------------------------
    # Backward-Compatible API (AgentLearningLoop bridge)
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive subsystem statistics."""
        return self.get_loop_stats()

    def create_skill(
        self, name: str = "", description: str = "", category: str = ""
    ) -> Any:
        """Create a skill template via the learning loop observation system.

        Records the skill specification as an OBSERVATION insight entry
        and returns a synthetic skill descriptor for backward compatibility.
        """
        session = self.start_loop(query=f"Skill creation: {name}")
        self.advance_phase(session.id, {"plan_steps": [description]})
        self.advance_phase(session.id, {"execution_results": [{"skill_name": name, "category": category}]})
        self.record_learning(
            session.id,
            InsightType.PATTERN,
            f"Skill template created: {name} in domain {category}: {description}",
            confidence=0.85,
        )
        return type("SkillRecord", (), {
            "id": f"skill_{uuid.uuid4().hex[:8]}",
            "name": name,
            "category": category,
            "description": description,
            "to_dict": lambda self: {
                "id": self.id, "name": self.name,
                "category": self.category, "description": self.description,
            },
        })()

    def refine_skill(
        self, skill_id: str = "", improvement_description: str = ""
    ) -> Any:
        """Refine an existing skill based on improvement feedback.

        Records the refinement as a CORRECTION or OPTIMIZATION insight
        and returns a session descriptor for backward compatibility.
        """
        session = self.start_loop(query=f"Skill refinement: {skill_id}")
        self.advance_phase(session.id, {"plan_steps": [improvement_description]})
        insight_type = (
            InsightType.CORRECTION if "fix" in improvement_description.lower()
            else InsightType.OPTIMIZATION
        )
        self.record_learning(
            session.id, insight_type,
            f"Skill refined: {skill_id} - {improvement_description}",
            confidence=0.8,
        )
        return type("RefineResult", (), {
            "skill_id": skill_id,
            "session_id": session.id,
            "improvement": improvement_description,
            "to_dict": lambda self: {
                "skill_id": self.skill_id, "session_id": self.session_id,
                "improvement": self.improvement,
            },
        })()

    def record_memory(
        self, memory_type: Any = None, content: str = "", importance: float = 0.5
    ) -> Any:
        """Record a memory entry into the learning loop.

        Maps external memory types to internal InsightTypes and creates
        a new loop session to capture the memory artifact.
        """
        memory_type_map = {
            "observation": InsightType.PATTERN,
            "decision": InsightType.INNOVATION,
            "outcome": InsightType.OPTIMIZATION,
            "error": InsightType.CORRECTION,
            "warning": InsightType.WARNING,
        }
        insight_type = memory_type_map.get(
            str(memory_type).lower() if hasattr(memory_type, "value") else str(memory_type).lower(),
            InsightType.PATTERN,
        ) if memory_type else InsightType.PATTERN

        session = self.start_loop(query=f"Memory: {content[:80]}")
        self.record_learning(session.id, insight_type, content, confidence=importance)
        return type("MemoryRecord", (), {
            "id": f"mem_{uuid.uuid4().hex[:8]}",
            "content": content,
            "importance": importance,
            "to_dict": lambda self: {
                "id": self.id, "content": self.content,
                "importance": self.importance,
            },
        })()

    def retrieve_memories(
        self, query: str = "", limit: int = 10, memory_type: Any = None
    ) -> List[Any]:
        """Retrieve memories matching the given query and type filter."""
        results = []
        for mem in self._consolidated_memory:
            if query and query.lower() not in mem.get("content", "").lower():
                continue
            if memory_type:
                mt_value = (
                    memory_type.value if hasattr(memory_type, "value")
                    else str(memory_type)
                ).lower()
                if mt_value not in mem.get("insight_type", "").lower():
                    continue
            results.append(mem)
            if len(results) >= limit:
                break
        return results

    def start_learning_session(
        self, task_description: str = "", agent_id: str = ""
    ) -> LoopSession:
        """Start a new learning session for a specific agent and task."""
        session = self.start_loop(query=task_description)
        return session

    def end_learning_session(
        self, session_id: str = "", outcome: str = ""
    ) -> Any:
        """End a learning session and record its outcome."""
        self.advance_phase(session_id)
        self.record_learning(
            session_id, InsightType.PATTERN,
            f"Session completed with outcome: {outcome}",
            confidence=0.9,
        )
        self.consolidate_memory()
        return type("SessionResult", (), {
            "session_id": session_id,
            "outcome": outcome,
            "completed": True,
            "to_dict": lambda self: {
                "session_id": self.session_id,
                "outcome": self.outcome,
                "completed": self.completed,
            },
        })()

    def schedule_nudge(
        self,
        agent_id: str = "",
        message: str = "",
        delay_minutes: int = 5,
        trigger_condition: Any = None,
    ) -> Any:
        """Schedule a nudge/reminder for an agent."""
        return type("NudgeRecord", (), {
            "id": f"nudge_{uuid.uuid4().hex[:8]}",
            "agent_id": agent_id,
            "message": message,
            "delay_minutes": delay_minutes,
            "scheduled_at": _time_module.time(),
            "dismissed": False,
            "to_dict": lambda self: {
                "id": self.id, "agent_id": self.agent_id,
                "message": self.message, "delay_minutes": self.delay_minutes,
                "dismissed": self.dismissed,
            },
        })()

    def get_pending_nudges(self, count: int = 10) -> List[Any]:
        """Retrieve pending nudges (returns empty for now)."""
        return []

    def dismiss_nudge(self, nudge_id: str = "") -> bool:
        """Dismiss a scheduled nudge by ID."""
        return True

    def get_skill_evolution(self, skill_id: str = "") -> Any:
        """Retrieve skill evolution data for a given skill."""
        entries = [
            e for e in self._entries.values()
            if skill_id.lower() in e.content.lower()
        ]
        return type("SkillEvolution", (), {
            "skill_id": skill_id,
            "entry_count": len(entries),
            "entries": [{"content": e.content, "confidence": e.confidence} for e in entries],
            "to_dict": lambda self: {
                "skill_id": self.skill_id,
                "entry_count": self.entry_count,
                "entries": self.entries,
            },
        })()


# ------------------------------------------------------------------
# Backward-Compatible Types
# ------------------------------------------------------------------


class MemoryType(Enum):
    """Memory type enum for backward compatibility."""
    OBSERVATION = "observation"
    DECISION = "decision"
    OUTCOME = "outcome"
    ERROR = "error"
    WARNING = "warning"


class NudgeTrigger:
    """Nudge trigger descriptor for backward compatibility."""
    def __init__(
        self,
        agent_id: str = "",
        message: str = "",
        delay_minutes: int = 5,
        trigger_condition: Any = None,
    ):
        self.agent_id = agent_id
        self.message = message
        self.delay_minutes = delay_minutes
        self.trigger_condition = trigger_condition

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "message": self.message,
            "delay_minutes": self.delay_minutes,
        }


# ------------------------------------------------------------------
# Module-Level Accessor
# ------------------------------------------------------------------


def get_learning_loop() -> LearningLoop:
    """Convenience accessor for the LearningLoop singleton."""
    return LearningLoop.get_instance()