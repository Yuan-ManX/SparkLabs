"""
SparkLabs Agent - Memory Orchestrator

Orchestrates persistent memory, skill creation, and experiential learning
across sessions. Maintains agent-curated memory stores with automatic
knowledge retrieval, skill improvement loops, and cross-session recall.

Architecture:
  AgentMemoryOrchestrator (Singleton)
    |-- Memory Store (short-term, long-term, episodic)
    |-- Skill Registry (creation, improvement, versioning)
    |-- Experience Learner (pattern extraction, knowledge consolidation)
    |-- Recall Engine (semantic search, contextual retrieval)
    |-- Nudge Scheduler (periodic memory reinforcement)
"""

from __future__ import annotations

import hashlib
import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MemoryCategory(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRANSIENT = "transient"


class SkillStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IMPROVING = "improving"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class NudgeTrigger(Enum):
    TIME_BASED = "time_based"
    CONTEXT_BASED = "context_based"
    EVENT_BASED = "event_based"
    MANUAL = "manual"


@dataclass
class MemoryEntry:
    memory_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: str = "short_term"
    priority: str = "medium"
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    embedding_hash: str = ""
    access_count: int = 0
    last_accessed: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    expires_at: float = 0.0
    linked_memories: List[str] = field(default_factory=list)
    confidence_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "category": self.category,
            "priority": self.priority,
            "content": self.content,
            "context": self.context,
            "tags": self.tags,
            "embedding_hash": self.embedding_hash,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "linked_memories": self.linked_memories,
            "confidence_score": self.confidence_score,
        }


@dataclass
class SkillDefinition:
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    version: int = 1
    status: str = "draft"
    trigger_patterns: List[str] = field(default_factory=list)
    action_sequence: List[Dict[str, Any]] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    usage_count: int = 0
    improvement_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = 0.0
    parent_skill_id: str = ""
    derived_skills: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status,
            "trigger_patterns": self.trigger_patterns,
            "action_sequence": self.action_sequence,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "improvement_history": self.improvement_history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "parent_skill_id": self.parent_skill_id,
            "derived_skills": self.derived_skills,
        }


@dataclass
class ExperienceRecord:
    experience_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    summary: str = ""
    extracted_patterns: List[Dict[str, Any]] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    skill_improvements: List[str] = field(default_factory=list)
    memory_links: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)
    consolidation_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "session_id": self.session_id,
            "summary": self.summary,
            "extracted_patterns": self.extracted_patterns,
            "lessons_learned": self.lessons_learned,
            "skill_improvements": self.skill_improvements,
            "memory_links": self.memory_links,
            "timestamp": self.timestamp,
            "consolidation_score": self.consolidation_score,
        }


@dataclass
class NudgeSchedule:
    nudge_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trigger_type: str = "time_based"
    interval_seconds: float = 3600.0
    target_memory_ids: List[str] = field(default_factory=list)
    target_skill_ids: List[str] = field(default_factory=list)
    last_triggered: float = 0.0
    next_trigger: float = 0.0
    enabled: bool = True
    max_triggers: int = 0
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nudge_id": self.nudge_id,
            "trigger_type": self.trigger_type,
            "interval_seconds": self.interval_seconds,
            "target_memory_ids": self.target_memory_ids,
            "target_skill_ids": self.target_skill_ids,
            "last_triggered": self.last_triggered,
            "next_trigger": self.next_trigger,
            "enabled": self.enabled,
            "max_triggers": self.max_triggers,
            "trigger_count": self.trigger_count,
        }


class AgentMemoryOrchestrator:
    """Orchestrates persistent memory, skill creation, and experiential learning.

    Maintains multi-tier memory stores, autonomous skill creation and improvement
    loops, cross-session knowledge retrieval, and periodic memory reinforcement
    nudges.
    """

    _instance: Optional["AgentMemoryOrchestrator"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_MEMORIES_PER_CATEGORY: int = 10000
    MAX_SKILLS: int = 500
    MAX_EXPERIENCES: int = 2000
    MAX_NUDGES: int = 100
    DEFAULT_MEMORY_TTL: float = 86400.0
    CONSOLIDATION_THRESHOLD: float = 0.6

    def __new__(cls) -> "AgentMemoryOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentMemoryOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        _time_module.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._memories: Dict[str, MemoryEntry] = {}
            self._skills: Dict[str, SkillDefinition] = {}
            self._experiences: Dict[str, ExperienceRecord] = {}
            self._nudges: Dict[str, NudgeSchedule] = {}
            self._memory_index: Dict[str, List[str]] = {}
            self._skill_index: Dict[str, List[str]] = {}
            self._total_memories_stored: int = 0
            self._total_skills_created: int = 0
            self._total_experiences_recorded: int = 0
            self._total_nudges_triggered: int = 0
            self._initialized = True

    def store_memory(
        self,
        content: str,
        category: str = "short_term",
        priority: str = "medium",
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        ttl: Optional[float] = None,
    ) -> MemoryEntry:
        _time_module.sleep(0.001)
        if context is None:
            context = {}
        if tags is None:
            tags = []
        if ttl is None:
            ttl = self.DEFAULT_MEMORY_TTL

        embedding_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        entry = MemoryEntry(
            category=category,
            priority=priority,
            content=content,
            context=context,
            tags=tags,
            embedding_hash=embedding_hash,
            expires_at=_time_module.time() + ttl,
        )

        self._memories[entry.memory_id] = entry
        self._total_memories_stored += 1

        for tag in tags:
            tag_key = tag.lower()
            if tag_key not in self._memory_index:
                self._memory_index[tag_key] = []
            self._memory_index[tag_key].append(entry.memory_id)

        cat_key = f"cat:{category}"
        if cat_key not in self._memory_index:
            self._memory_index[cat_key] = []
        self._memory_index[cat_key].append(entry.memory_id)

        return entry

    def retrieve_memories(
        self,
        query_tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        _time_module.sleep(0.001)
        results: List[MemoryEntry] = []
        now = _time_module.time()

        for entry in self._memories.values():
            if entry.expires_at > 0 and entry.expires_at < now:
                continue
            if category and entry.category != category:
                continue
            if priority and entry.priority != priority:
                continue
            if entry.confidence_score < min_confidence:
                continue
            if query_tags:
                entry_tags = {t.lower() for t in entry.tags}
                query_set = {t.lower() for t in query_tags}
                if not query_set.intersection(entry_tags):
                    continue

            results.append(entry)

        results.sort(key=lambda e: (e.confidence_score, e.access_count), reverse=True)

        for entry in results[:limit]:
            entry.access_count += 1
            entry.last_accessed = now

        return results[:limit]

    def recall_by_context(
        self,
        context_key: str,
        context_value: Any,
        limit: int = 20,
    ) -> List[MemoryEntry]:
        _time_module.sleep(0.001)
        results: List[MemoryEntry] = []
        now = _time_module.time()

        for entry in self._memories.values():
            if entry.expires_at > 0 and entry.expires_at < now:
                continue
            if entry.context.get(context_key) == context_value:
                results.append(entry)

        results.sort(key=lambda e: e.last_accessed, reverse=True)

        for entry in results[:limit]:
            entry.access_count += 1
            entry.last_accessed = now

        return results[:limit]

    def link_memories(
        self,
        memory_id_a: str,
        memory_id_b: str,
        bidirectional: bool = True,
    ) -> bool:
        if memory_id_a not in self._memories or memory_id_b not in self._memories:
            return False

        mem_a = self._memories[memory_id_a]
        mem_b = self._memories[memory_id_b]

        if memory_id_b not in mem_a.linked_memories:
            mem_a.linked_memories.append(memory_id_b)
        if bidirectional and memory_id_a not in mem_b.linked_memories:
            mem_b.linked_memories.append(memory_id_a)

        return True

    def consolidate_memories(
        self,
        memory_ids: List[str],
        new_category: str = "long_term",
    ) -> Optional[MemoryEntry]:
        entries = [self._memories[mid] for mid in memory_ids if mid in self._memories]
        if not entries:
            return None

        combined_content = "\n".join(e.content for e in entries)
        combined_tags = list(set(t for e in entries for t in e.tags))
        combined_context = {}
        for e in entries:
            for k, v in e.context.items():
                if k in combined_context:
                    if isinstance(combined_context[k], list):
                        combined_context[k].append(v)
                    else:
                        combined_context[k] = [combined_context[k], v]
                else:
                    combined_context[k] = v

        avg_confidence = sum(e.confidence_score for e in entries) / len(entries)

        consolidated = self.store_memory(
            content=combined_content,
            category=new_category,
            priority="high",
            context=combined_context,
            tags=combined_tags,
        )
        consolidated.confidence_score = avg_confidence
        consolidated.linked_memories = memory_ids

        return consolidated

    def create_skill(
        self,
        name: str,
        description: str,
        trigger_patterns: Optional[List[str]] = None,
        action_sequence: Optional[List[Dict[str, Any]]] = None,
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
    ) -> SkillDefinition:
        _time_module.sleep(0.001)
        if trigger_patterns is None:
            trigger_patterns = []
        if action_sequence is None:
            action_sequence = []
        if preconditions is None:
            preconditions = []
        if postconditions is None:
            postconditions = []

        skill = SkillDefinition(
            name=name,
            description=description,
            trigger_patterns=trigger_patterns,
            action_sequence=action_sequence,
            preconditions=preconditions,
            postconditions=postconditions,
            status="draft",
        )

        self._skills[skill.skill_id] = skill
        self._total_skills_created += 1

        name_key = name.lower()
        if name_key not in self._skill_index:
            self._skill_index[name_key] = []
        self._skill_index[name_key].append(skill.skill_id)

        return skill

    def improve_skill(
        self,
        skill_id: str,
        success: bool,
        improvement_notes: str = "",
        new_action_sequence: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[SkillDefinition]:
        if skill_id not in self._skills:
            return None

        skill = self._skills[skill_id]
        now = _time_module.time()

        skill.usage_count += 1

        if success:
            skill.success_rate = (
                (skill.success_rate * (skill.usage_count - 1) + 1.0) / skill.usage_count
            )
        else:
            skill.success_rate = (
                (skill.success_rate * (skill.usage_count - 1)) / skill.usage_count
            )

        improvement = {
            "timestamp": now,
            "success": success,
            "notes": improvement_notes,
            "previous_version": skill.version,
            "previous_success_rate": skill.success_rate,
        }
        skill.improvement_history.append(improvement)

        if new_action_sequence:
            skill.version += 1
            skill.action_sequence = new_action_sequence
            skill.status = "improving"

        if skill.usage_count >= 5 and skill.success_rate >= 0.8:
            skill.status = "active"

        skill.updated_at = now
        return skill

    def derive_skill(
        self,
        parent_skill_id: str,
        name: str,
        description: str,
        modifications: Dict[str, Any],
    ) -> Optional[SkillDefinition]:
        if parent_skill_id not in self._skills:
            return None

        parent = self._skills[parent_skill_id]

        new_skill = SkillDefinition(
            name=name,
            description=description,
            trigger_patterns=list(parent.trigger_patterns),
            action_sequence=list(parent.action_sequence),
            preconditions=list(parent.preconditions),
            postconditions=list(parent.postconditions),
            parent_skill_id=parent_skill_id,
        )

        if "trigger_patterns" in modifications:
            new_skill.trigger_patterns = modifications["trigger_patterns"]
        if "action_sequence" in modifications:
            new_skill.action_sequence = modifications["action_sequence"]
        if "preconditions" in modifications:
            new_skill.preconditions = modifications["preconditions"]

        self._skills[new_skill.skill_id] = new_skill
        self._total_skills_created += 1
        parent.derived_skills.append(new_skill.skill_id)

        return new_skill

    def find_skills_by_trigger(self, trigger_text: str) -> List[SkillDefinition]:
        trigger_lower = trigger_text.lower()
        results: List[SkillDefinition] = []

        for skill in self._skills.values():
            if skill.status in ("deprecated", "archived"):
                continue
            for pattern in skill.trigger_patterns:
                if pattern.lower() in trigger_lower:
                    results.append(skill)
                    break

        results.sort(key=lambda s: (s.success_rate, s.usage_count), reverse=True)
        return results

    def record_experience(
        self,
        session_id: str,
        summary: str,
        patterns: Optional[List[Dict[str, Any]]] = None,
        lessons: Optional[List[str]] = None,
        skill_ids: Optional[List[str]] = None,
    ) -> ExperienceRecord:
        _time_module.sleep(0.001)
        if patterns is None:
            patterns = []
        if lessons is None:
            lessons = []
        if skill_ids is None:
            skill_ids = []

        experience = ExperienceRecord(
            session_id=session_id,
            summary=summary,
            extracted_patterns=patterns,
            lessons_learned=lessons,
            skill_improvements=skill_ids,
        )

        consolidation = 0.3 + 0.5 * min(1.0, len(patterns) / 5.0) + 0.2 * min(1.0, len(lessons) / 3.0)
        experience.consolidation_score = consolidation

        self._experiences[experience.experience_id] = experience
        self._total_experiences_recorded += 1

        if consolidation >= self.CONSOLIDATION_THRESHOLD:
            for lesson in lessons:
                self.store_memory(
                    content=lesson,
                    category="semantic",
                    priority="high",
                    context={"source": "experience", "experience_id": experience.experience_id},
                    tags=["learned_lesson", "experience"],
                )

        return experience

    def extract_patterns_from_experiences(
        self,
        min_occurrences: int = 2,
    ) -> List[Dict[str, Any]]:
        pattern_counts: Dict[str, Dict[str, Any]] = {}

        for exp in self._experiences.values():
            for pattern in exp.extracted_patterns:
                pattern_key = pattern.get("name", "")
                if not pattern_key:
                    continue
                if pattern_key not in pattern_counts:
                    pattern_counts[pattern_key] = {
                        "name": pattern_key,
                        "occurrences": 0,
                        "examples": [],
                        "total_consolidation": 0.0,
                    }
                pattern_counts[pattern_key]["occurrences"] += 1
                pattern_counts[pattern_key]["examples"].append(pattern.get("example", ""))
                pattern_counts[pattern_key]["total_consolidation"] += exp.consolidation_score

        significant = []
        for key, data in pattern_counts.items():
            if data["occurrences"] >= min_occurrences:
                data["confidence"] = data["total_consolidation"] / data["occurrences"]
                significant.append(data)

        significant.sort(key=lambda p: p["confidence"], reverse=True)
        return significant

    def schedule_nudge(
        self,
        trigger_type: str = "time_based",
        interval_seconds: float = 3600.0,
        target_memory_ids: Optional[List[str]] = None,
        target_skill_ids: Optional[List[str]] = None,
    ) -> NudgeSchedule:
        if target_memory_ids is None:
            target_memory_ids = []
        if target_skill_ids is None:
            target_skill_ids = []

        now = _time_module.time()
        nudge = NudgeSchedule(
            trigger_type=trigger_type,
            interval_seconds=interval_seconds,
            target_memory_ids=target_memory_ids,
            target_skill_ids=target_skill_ids,
            next_trigger=now + interval_seconds,
        )

        self._nudges[nudge.nudge_id] = nudge
        return nudge

    def check_nudges(self) -> List[NudgeSchedule]:
        now = _time_module.time()
        triggered: List[NudgeSchedule] = []

        for nudge in self._nudges.values():
            if not nudge.enabled:
                continue
            if nudge.max_triggers > 0 and nudge.trigger_count >= nudge.max_triggers:
                continue
            if now >= nudge.next_trigger:
                nudge.trigger_count += 1
                nudge.last_triggered = now
                nudge.next_trigger = now + nudge.interval_seconds
                triggered.append(nudge)
                self._total_nudges_triggered += 1

        return triggered

    def get_memory_stats(self) -> Dict[str, Any]:
        categories: Dict[str, int] = {}
        priorities: Dict[str, int] = {}
        for m in self._memories.values():
            categories[m.category] = categories.get(m.category, 0) + 1
            priorities[m.priority] = priorities.get(m.priority, 0) + 1

        return {
            "total_memories": len(self._memories),
            "by_category": categories,
            "by_priority": priorities,
            "total_stored": self._total_memories_stored,
        }

    def get_skill_stats(self) -> Dict[str, Any]:
        statuses: Dict[str, int] = {}
        for s in self._skills.values():
            statuses[s.status] = statuses.get(s.status, 0) + 1

        return {
            "total_skills": len(self._skills),
            "by_status": statuses,
            "total_created": self._total_skills_created,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "memory": self.get_memory_stats(),
            "skills": self.get_skill_stats(),
            "total_experiences": len(self._experiences),
            "total_experiences_recorded": self._total_experiences_recorded,
            "total_nudges": len(self._nudges),
            "total_nudges_triggered": self._total_nudges_triggered,
        }

    def list_memories(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._memories.values()]

    def list_skills(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._skills.values()]

    def list_experiences(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._experiences.values()]

    def list_nudges(self) -> List[Dict[str, Any]]:
        return [n.to_dict() for n in self._nudges.values()]


def get_memory_orchestrator() -> AgentMemoryOrchestrator:
    return AgentMemoryOrchestrator.get_instance()