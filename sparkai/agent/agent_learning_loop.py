"""
SparkLabs Agent - Learning Loop

A self-improving agent system that captures skills from operational
experience, refines them through iterative use, builds persistent
memory across sessions, and nudges knowledge retention over time.
The loop progresses through five phases — capture, analyze, generalize,
apply, and verify — to continuously elevate agent capability.

Architecture:
  AgentLearningLoop
    |-- SkillRegistry (creates and refines LearnedSkill instances)
    |-- MemoryStore (records and retrieves MemoryEntry by type/query)
    |-- SessionManager (tracks LearningSession lifecycle)
    |-- NudgeScheduler (queues and dismisses NudgeEvent triggers)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SkillState(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    REFINING = "refining"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class MemoryType(Enum):
    OBSERVATION = "observation"
    PATTERN = "pattern"
    INSIGHT = "insight"
    PROCEDURE = "procedure"
    PREFERENCE = "preference"


class NudgeTrigger(Enum):
    INTERVAL = "interval"
    CONTEXT_SWITCH = "context_switch"
    ERROR = "error"
    IDLE = "idle"
    MILESTONE = "milestone"


class LearningPhase(Enum):
    CAPTURE = "capture"
    ANALYZE = "analyze"
    GENERALIZE = "generalize"
    APPLY = "apply"
    VERIFY = "verify"


@dataclass
class LearnedSkill:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: str = ""
    source_experience: str = ""
    state: SkillState = SkillState.DRAFT
    version: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)
    improvement_log: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "source_experience": self.source_experience,
            "state": self.state.value,
            "version": self.version,
            "parameters": self.parameters,
            "improvement_log": self.improvement_log,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    memory_type: MemoryType = MemoryType.OBSERVATION
    content: str = ""
    context_tags: List[str] = field(default_factory=list)
    importance: float = 0.0
    embedding: Optional[List[float]] = None
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "context_tags": self.context_tags,
            "importance": round(self.importance, 2),
            "access_count": self.access_count,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
        }


@dataclass
class LearningSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_description: str = ""
    agent_id: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    outcome: str = ""
    insights: List[str] = field(default_factory=list)
    phase: LearningPhase = LearningPhase.CAPTURE
    skills_used: List[str] = field(default_factory=list)
    memories_created: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_description": self.task_description,
            "agent_id": self.agent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "outcome": self.outcome,
            "insights": self.insights,
            "phase": self.phase.value,
            "skills_used": self.skills_used,
            "memories_created": self.memories_created,
        }


@dataclass
class NudgeEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trigger: NudgeTrigger = NudgeTrigger.INTERVAL
    message: str = ""
    priority: int = 0
    target_agent: str = ""
    scheduled_at: float = field(default_factory=time.time)
    dismissed: bool = False
    dismissed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trigger": self.trigger.value,
            "message": self.message,
            "priority": self.priority,
            "target_agent": self.target_agent,
            "scheduled_at": self.scheduled_at,
            "dismissed": self.dismissed,
            "dismissed_at": self.dismissed_at,
        }


class AgentLearningLoop:
    """Self-improving agent system that learns from experience over time."""

    _instance: Optional["AgentLearningLoop"] = None
    _lock = threading.RLock()

    _PHASE_ORDER: Dict[LearningPhase, int] = {
        LearningPhase.CAPTURE: 0,
        LearningPhase.ANALYZE: 1,
        LearningPhase.GENERALIZE: 2,
        LearningPhase.APPLY: 3,
        LearningPhase.VERIFY: 4,
    }

    _IMPORTANCE_DECAY_RATE: float = 0.05
    _DEFAULT_RETRIEVAL_LIMIT: int = 20
    _MAX_NUDGE_QUEUE: int = 100

    def __init__(self) -> None:
        self._skills: Dict[str, LearnedSkill] = {}
        self._memories: Dict[str, MemoryEntry] = {}
        self._sessions: List[LearningSession] = []
        self._nudge_queue: List[NudgeEvent] = []

    @classmethod
    def get_instance(cls) -> "AgentLearningLoop":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Skill Lifecycle ----

    def create_skill(self,
                     name: str,
                     description: str,
                     category: str = "",
                     source_experience: str = "") -> LearnedSkill:
        skill = LearnedSkill(
            name=name,
            description=description,
            category=category,
            source_experience=source_experience,
            state=SkillState.DRAFT,
            version=1,
        )
        self._skills[skill.id] = skill
        return skill

    def refine_skill(self,
                     skill_id: str,
                     improvement_description: str = "",
                     new_parameters: Optional[Dict[str, Any]] = None) -> Optional[LearnedSkill]:
        skill = self._skills.get(skill_id)
        if skill is None or skill.state == SkillState.DEPRECATED:
            return None

        previous_state = skill.state
        skill.state = SkillState.REFINING
        skill.version += 1
        skill.updated_at = time.time()

        if new_parameters:
            skill.parameters.update(new_parameters)

        skill.improvement_log.append({
            "version": skill.version,
            "description": improvement_description,
            "previous_state": previous_state.value,
            "timestamp": skill.updated_at,
        })

        total_improvements = len(skill.improvement_log)
        if total_improvements >= 5:
            skill.state = SkillState.STABLE
        elif total_improvements >= 2:
            skill.state = SkillState.ACTIVE

        return skill

    def deprecate_skill(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        skill.state = SkillState.DEPRECATED
        skill.updated_at = time.time()
        return True

    def get_skill(self, skill_id: str) -> Optional[LearnedSkill]:
        return self._skills.get(skill_id)

    def get_skills_by_category(self, category: str) -> List[LearnedSkill]:
        return [s for s in self._skills.values() if s.category == category]

    def get_skill_evolution(self, skill_id: str) -> Dict[str, Any]:
        skill = self._skills.get(skill_id)
        if skill is None:
            return {}
        return {
            "skill": skill.to_dict(),
            "total_improvements": len(skill.improvement_log),
            "state_transitions": [
                entry["previous_state"] + " → " + skill.state.value
                if i == len(skill.improvement_log) - 1
                else entry["previous_state"]
                for i, entry in enumerate(skill.improvement_log)
            ],
            "lifespan_seconds": time.time() - skill.created_at,
        }

    # ---- Memory Operations ----

    def record_memory(self,
                      memory_type: MemoryType,
                      content: str,
                      context_tags: Optional[List[str]] = None,
                      importance: float = 0.5) -> MemoryEntry:
        clamped_importance = max(0.0, min(1.0, importance))
        entry = MemoryEntry(
            memory_type=memory_type,
            content=content,
            context_tags=context_tags or [],
            importance=clamped_importance,
        )
        self._memories[entry.id] = entry
        return entry

    def retrieve_memories(self,
                          query: str = "",
                          memory_type: Optional[MemoryType] = None,
                          limit: int = 20) -> List[MemoryEntry]:
        candidates: List[MemoryEntry] = []
        query_lower = query.lower() if query else ""

        for entry in self._memories.values():
            if memory_type is not None and entry.memory_type != memory_type:
                continue
            if query_lower:
                content_match = query_lower in entry.content.lower()
                tag_match = any(query_lower in tag.lower() for tag in entry.context_tags)
                if not content_match and not tag_match:
                    continue
            candidates.append(entry)

        for entry in candidates:
            entry.access_count += 1
            entry.last_accessed_at = time.time()

        candidates.sort(key=lambda e: e.importance * math.log(e.access_count + 2), reverse=True)
        return candidates[:limit]

    def forget_memory(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def decay_memories(self, threshold: float = 0.05) -> int:
        decayed_count = 0
        now = time.time()
        to_forget: List[str] = []
        for entry in self._memories.values():
            age_hours = (now - entry.created_at) / 3600.0
            entry.importance -= self._IMPORTANCE_DECAY_RATE * age_hours
            if entry.importance <= 0:
                entry.importance = 0
            if entry.importance < threshold:
                to_forget.append(entry.id)
        for mid in to_forget:
            del self._memories[mid]
            decayed_count += 1
        return decayed_count

    # ---- Session Management ----

    def start_learning_session(self,
                               task_description: str,
                               agent_id: str = "") -> LearningSession:
        session = LearningSession(
            task_description=task_description,
            agent_id=agent_id,
            phase=LearningPhase.CAPTURE,
        )
        self._sessions.append(session)
        return session

    def end_learning_session(self,
                             session_id: str,
                             outcome: str = "",
                             insights: Optional[List[str]] = None) -> Optional[LearningSession]:
        for session in self._sessions:
            if session.id == session_id and session.end_time is None:
                session.end_time = time.time()
                session.outcome = outcome
                session.insights = insights or []
                session.phase = self._determine_session_phase(session)
                return session
        return None

    def get_active_sessions(self) -> List[LearningSession]:
        return [s for s in self._sessions if s.end_time is None]

    def get_session_history(self, agent_id: str = "") -> List[LearningSession]:
        if not agent_id:
            return list(self._sessions)
        return [s for s in self._sessions if s.agent_id == agent_id]

    # ---- Nudge System ----

    def schedule_nudge(self,
                       trigger: NudgeTrigger,
                       message: str,
                       priority: int = 0,
                       target_agent: str = "") -> NudgeEvent:
        event = NudgeEvent(
            trigger=trigger,
            message=message,
            priority=priority,
            target_agent=target_agent,
        )
        self._nudge_queue.append(event)
        self._nudge_queue.sort(key=lambda e: e.priority, reverse=True)
        if len(self._nudge_queue) > self._MAX_NUDGE_QUEUE:
            self._nudge_queue = self._nudge_queue[: self._MAX_NUDGE_QUEUE]
        return event

    def dismiss_nudge(self, nudge_id: str) -> bool:
        for event in self._nudge_queue:
            if event.id == nudge_id and not event.dismissed:
                event.dismissed = True
                event.dismissed_at = time.time()
                return True
        return False

    def get_pending_nudges(self, count: int = 10) -> List[NudgeEvent]:
        pending = [e for e in self._nudge_queue if not e.dismissed]
        return pending[:count]

    def get_nudge_stats(self) -> Dict[str, int]:
        total = len(self._nudge_queue)
        dismissed = sum(1 for e in self._nudge_queue if e.dismissed)
        return {
            "total": total,
            "pending": total - dismissed,
            "dismissed": dismissed,
        }

    # ---- Stats & Reporting ----

    def get_stats(self) -> Dict[str, Any]:
        skill_counts: Dict[str, int] = {}
        for skill in self._skills.values():
            key = skill.state.value
            skill_counts[key] = skill_counts.get(key, 0) + 1

        memory_counts: Dict[str, int] = {}
        for mem in self._memories.values():
            key = mem.memory_type.value
            memory_counts[key] = memory_counts.get(key, 0) + 1

        session_counts: Dict[str, int] = {}
        for session in self._sessions:
            key = session.phase.value
            session_counts[key] = session_counts.get(key, 0) + 1

        completed_sessions = [s for s in self._sessions if s.end_time is not None]
        avg_duration = 0.0
        if completed_sessions:
            durations = [(s.end_time or 0) - s.start_time for s in completed_sessions]
            avg_duration = sum(durations) / len(durations)

        return {
            "total_skills": len(self._skills),
            "skills_by_state": skill_counts,
            "total_memories": len(self._memories),
            "memories_by_type": memory_counts,
            "total_sessions": len(self._sessions),
            "active_sessions": len(self.get_active_sessions()),
            "sessions_by_phase": session_counts,
            "average_session_duration_seconds": round(avg_duration, 1),
            "pending_nudges": len(self.get_pending_nudges()),
            "total_nudges": len(self._nudge_queue),
        }

    def reset(self) -> None:
        with self._lock:
            self._skills.clear()
            self._memories.clear()
            self._sessions.clear()
            self._nudge_queue.clear()

    # ---- Helpers ----

    @staticmethod
    def _determine_session_phase(session: LearningSession) -> LearningPhase:
        if not session.outcome:
            return LearningPhase.CAPTURE
        if not session.insights:
            return LearningPhase.ANALYZE
        if len(session.insights) < 3:
            return LearningPhase.GENERALIZE
        if session.skills_used:
            return LearningPhase.APPLY
        return LearningPhase.VERIFY


def get_learning_loop() -> AgentLearningLoop:
    return AgentLearningLoop.get_instance()