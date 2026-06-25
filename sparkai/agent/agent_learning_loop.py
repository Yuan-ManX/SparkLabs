"""
SparkLabs Agent Learning Loop - Self-Improving Agent with Memory Hierarchy

Core self-improving agent system that learns from every interaction through
a three-tier memory architecture and autonomous skill generation.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class MemoryLayer(Enum):
    """Memory tier classification."""
    EPISODIC = "episodic"        # What happened - conversation and task outcomes
    SEMANTIC = "semantic"        # What is known - preferences, context, facts
    PROCEDURAL = "procedural"    # How to do it - skills, patterns, workflows
    REFLECTIVE = "reflective"    # Meta-cognition - self-analysis and improvement


class LearningPhase(Enum):
    """Phases of the self-improving learning loop."""
    OBSERVE = "observe"          # Gather context and understand the task
    EXECUTE = "execute"          # Perform the task using available tools
    EVALUATE = "evaluate"        # Assess outcomes and identify patterns
    CONSOLIDATE = "consolidate"  # Distill learnings into persistent memory
    IMPROVE = "improve"          # Generate or update skills from experience


class SkillLifecycle(Enum):
    """Lifecycle stages of an autonomous skill."""
    DRAFT = "draft"              # Newly created, not yet validated
    ACTIVE = "active"            # Validated and in use
    DEPRECATED = "deprecated"    # No longer useful, pending removal
    ARCHIVED = "archived"        # Stored for reference, not active


@dataclass
class MemoryEntry:
    """A single entry in the memory system."""
    entry_id: str
    layer: MemoryLayer
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "layer": self.layer.value,
            "content": self.content,
            "metadata": self.metadata,
            "importance": self.importance,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "tags": self.tags,
        }


@dataclass
class SkillManifest:
    """A reusable skill generated from learning experiences."""
    skill_id: str
    name: str
    description: str
    trigger_patterns: List[str]
    steps: List[Dict[str, Any]]
    prerequisites: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    usage_count: int = 0
    lifecycle: SkillLifecycle = SkillLifecycle.DRAFT
    parent_skill_id: Optional[str] = None
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "trigger_patterns": self.trigger_patterns,
            "steps": self.steps,
            "prerequisites": self.prerequisites,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "lifecycle": self.lifecycle.value,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class LearningSession:
    """Tracks a single learning session from task to improvement."""
    session_id: str
    task_description: str
    phase: LearningPhase = LearningPhase.OBSERVE
    observations: List[Dict[str, Any]] = field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    outcomes: Dict[str, Any] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    skills_generated: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    success: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_description": self.task_description,
            "phase": self.phase.value,
            "observations": self.observations,
            "actions_taken": self.actions_taken,
            "outcomes": self.outcomes,
            "lessons_learned": self.lessons_learned,
            "skills_generated": self.skills_generated,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "success": self.success,
        }


class MemoryStore:
    """Three-tier memory storage with importance-based retention."""

    def __init__(self, max_episodic: int = 10000, max_semantic: int = 5000,
                 max_procedural: int = 2000, max_reflective: int = 1000) -> None:
        self._episodic: List[MemoryEntry] = []
        self._semantic: List[MemoryEntry] = []
        self._procedural: List[MemoryEntry] = []
        self._reflective: List[MemoryEntry] = []
        self._max_sizes: Dict[MemoryLayer, int] = {
            MemoryLayer.EPISODIC: max_episodic,
            MemoryLayer.SEMANTIC: max_semantic,
            MemoryLayer.PROCEDURAL: max_procedural,
            MemoryLayer.REFLECTIVE: max_reflective,
        }
        self._lock = threading.RLock()

    def _get_layer(self, layer: MemoryLayer) -> List[MemoryEntry]:
        if layer == MemoryLayer.EPISODIC:
            return self._episodic
        elif layer == MemoryLayer.SEMANTIC:
            return self._semantic
        elif layer == MemoryLayer.PROCEDURAL:
            return self._procedural
        return self._reflective

    def store(self, entry: MemoryEntry) -> None:
        with self._lock:
            layer_entries = self._get_layer(entry.layer)
            layer_entries.append(entry)
            max_size = self._max_sizes[entry.layer]
            if len(layer_entries) > max_size:
                # Remove least important entries first
                layer_entries.sort(key=lambda e: (e.importance, e.accessed_at))
                layer_entries[:len(layer_entries) - max_size] = []

    def retrieve(self, layer: MemoryLayer, query_tags: Optional[List[str]] = None,
                 min_importance: float = 0.0, limit: int = 50) -> List[MemoryEntry]:
        with self._lock:
            entries = self._get_layer(layer)
            results = entries[:]
            if query_tags:
                results = [e for e in results
                          if any(t in e.tags for t in query_tags)]
            results = [e for e in results if e.importance >= min_importance]
            results.sort(key=lambda e: (e.importance, e.accessed_at), reverse=True)
            for e in results[:limit]:
                e.access_count += 1
                e.accessed_at = time.time()
            return results[:limit]

    def search(self, keyword: str, layers: Optional[List[MemoryLayer]] = None,
               limit: int = 20) -> List[MemoryEntry]:
        with self._lock:
            search_layers = layers or list(MemoryLayer)
            results: List[MemoryEntry] = []
            for layer in search_layers:
                for entry in self._get_layer(layer):
                    if keyword.lower() in entry.content.lower():
                        results.append(entry)
            results.sort(key=lambda e: (e.importance, e.accessed_at), reverse=True)
            return results[:limit]

    def consolidate(self, source_layer: MemoryLayer, target_layer: MemoryLayer,
                    entry_ids: List[str]) -> None:
        """Move or copy entries between memory layers."""
        with self._lock:
            source = self._get_layer(source_layer)
            for entry in source:
                if entry.entry_id in entry_ids:
                    new_entry = MemoryEntry(
                        entry_id=f"consolidated_{uuid.uuid4().hex[:12]}",
                        layer=target_layer,
                        content=entry.content,
                        metadata={**entry.metadata, "consolidated_from": source_layer.value},
                        importance=min(entry.importance * 1.2, 1.0),
                        tags=entry.tags,
                    )
                    self._get_layer(target_layer).append(new_entry)

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "episodic": {"count": len(self._episodic),
                            "max": self._max_sizes[MemoryLayer.EPISODIC]},
                "semantic": {"count": len(self._semantic),
                            "max": self._max_sizes[MemoryLayer.SEMANTIC]},
                "procedural": {"count": len(self._procedural),
                              "max": self._max_sizes[MemoryLayer.PROCEDURAL]},
                "reflective": {"count": len(self._reflective),
                              "max": self._max_sizes[MemoryLayer.REFLECTIVE]},
            }


class SkillLibrary:
    """Library of autonomously generated and refined skills."""

    def __init__(self, max_skills: int = 500) -> None:
        self._skills: Dict[str, SkillManifest] = {}
        self._max_skills = max_skills
        self._lock = threading.RLock()

    def register(self, skill: SkillManifest) -> bool:
        with self._lock:
            if len(self._skills) >= self._max_skills:
                # Evict least used deprecated skills
                deprecated = [s for s in self._skills.values()
                             if s.lifecycle == SkillLifecycle.DEPRECATED]
                deprecated.sort(key=lambda s: s.usage_count)
                for s in deprecated[:max(1, len(deprecated) // 2)]:
                    del self._skills[s.skill_id]
                if len(self._skills) >= self._max_skills:
                    return False
            self._skills[skill.skill_id] = skill
            return True

    def get(self, skill_id: str) -> Optional[SkillManifest]:
        with self._lock:
            return self._skills.get(skill_id)

    def find_by_trigger(self, trigger: str) -> List[SkillManifest]:
        with self._lock:
            results = []
            for skill in self._skills.values():
                if skill.lifecycle != SkillLifecycle.ACTIVE:
                    continue
                for pattern in skill.trigger_patterns:
                    if pattern.lower() in trigger.lower():
                        results.append(skill)
                        break
            results.sort(key=lambda s: (s.success_rate, s.usage_count), reverse=True)
            return results

    def record_usage(self, skill_id: str, success: bool) -> None:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill:
                skill.usage_count += 1
                # Update success rate with exponential moving average
                alpha = 0.1
                skill.success_rate = (1 - alpha) * skill.success_rate + alpha * (1.0 if success else 0.0)
                skill.updated_at = time.time()

    def get_all_active(self) -> List[SkillManifest]:
        with self._lock:
            return [s for s in self._skills.values()
                   if s.lifecycle == SkillLifecycle.ACTIVE]

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            drafts = sum(1 for s in self._skills.values()
                        if s.lifecycle == SkillLifecycle.DRAFT)
            active = sum(1 for s in self._skills.values()
                        if s.lifecycle == SkillLifecycle.ACTIVE)
            deprecated = sum(1 for s in self._skills.values()
                            if s.lifecycle == SkillLifecycle.DEPRECATED)
            archived = sum(1 for s in self._skills.values()
                          if s.lifecycle == SkillLifecycle.ARCHIVED)
            return {
                "total": len(self._skills),
                "draft": drafts,
                "active": active,
                "deprecated": deprecated,
                "archived": archived,
                "average_success_rate": (
                    sum(s.success_rate for s in self._skills.values()) / max(len(self._skills), 1)
                ),
            }


class LearningLoopEngine:
    """Core self-improving learning loop based on the Do-Learn-Improve cycle.

    This engine drives continuous agent improvement through three phases:
    1. DO: Execute tasks using best available tools and reasoning
    2. LEARN: Evaluate outcomes, record in multi-tier memory
    3. IMPROVE: Generate and refine reusable skills from patterns
    """

    _instance: Optional["LearningLoopEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use LearningLoopEngine.get_instance()")
        self._memory_store = MemoryStore()
        self._skill_library = SkillLibrary()
        self._active_sessions: Dict[str, LearningSession] = {}
        self._session_history: List[LearningSession] = []
        self._initialized: bool = False
        self._improvement_callbacks: List[Callable[[SkillManifest], None]] = []
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "LearningLoopEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        with self._lock:
            self._initialized = True

    def start_session(self, task_description: str) -> LearningSession:
        session = LearningSession(
            session_id=f"session_{uuid.uuid4().hex[:12]}",
            task_description=task_description,
        )
        with self._lock:
            self._active_sessions[session.session_id] = session
            self._record_observation(
                session,
                "session_started",
                {"task": task_description},
                MemoryLayer.EPISODIC,
            )
        return session

    def observe(self, session_id: str, observation_type: str,
                data: Dict[str, Any]) -> None:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session:
                session.phase = LearningPhase.OBSERVE
                self._record_observation(session, observation_type, data,
                                        MemoryLayer.EPISODIC)

    def record_action(self, session_id: str, action: str,
                      params: Dict[str, Any], result: Any) -> None:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session:
                session.phase = LearningPhase.EXECUTE
                action_record = {
                    "action": action,
                    "params": params,
                    "result": str(result)[:500],
                    "timestamp": time.time(),
                }
                session.actions_taken.append(action_record)
                self._record_observation(
                    session, f"action_{action}",
                    action_record, MemoryLayer.EPISODIC,
                )

    def evaluate(self, session_id: str, success: bool,
                 metrics: Optional[Dict[str, Any]] = None) -> List[str]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                return []
            session.phase = LearningPhase.EVALUATE
            session.success = success
            session.outcomes = {"success": success, "metrics": metrics or {}}

            # Generate lessons learned
            lessons = self._derive_lessons(session)
            session.lessons_learned = lessons

            # Store as semantic memory for future reference
            for lesson in lessons:
                entry = MemoryEntry(
                    entry_id=f"mem_{uuid.uuid4().hex[:12]}",
                    layer=MemoryLayer.SEMANTIC,
                    content=lesson,
                    importance=0.7 if success else 0.9,
                    tags=["lesson", "success" if success else "failure"],
                )
                self._memory_store.store(entry)

            return lessons

    def consolidate(self, session_id: str) -> Optional[SkillManifest]:
        """Consolidate learnings and potentially generate a new skill."""
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                return None
            session.phase = LearningPhase.CONSOLIDATE

            # Check if this session pattern warrants a new skill
            skill = self._generate_skill(session)
            if skill:
                session.phase = LearningPhase.IMPROVE
                session.skills_generated.append(skill.skill_id)
                session.completed_at = time.time()

                # Move session to history
                self._session_history.append(session)
                del self._active_sessions[session_id]

                # Notify improvement callbacks
                for callback in self._improvement_callbacks:
                    try:
                        callback(skill)
                    except Exception:
                        pass
                return skill

            session.completed_at = time.time()
            self._session_history.append(session)
            del self._active_sessions[session_id]
            return None

    def add_improvement_callback(self, callback: Callable[[SkillManifest], None]) -> None:
        with self._lock:
            self._improvement_callbacks.append(callback)

    def find_skill_for_task(self, task_description: str) -> Optional[SkillManifest]:
        skills = self._skill_library.find_by_trigger(task_description)
        return skills[0] if skills else None

    def _record_observation(self, session: LearningSession,
                            obs_type: str, data: Dict[str, Any],
                            layer: MemoryLayer) -> None:
        entry = MemoryEntry(
            entry_id=f"mem_{uuid.uuid4().hex[:12]}",
            layer=layer,
            content=f"{obs_type}: {json.dumps(data, default=str)}",
            metadata={"session_id": session.session_id, "type": obs_type},
            importance=0.5,
            tags=[obs_type, session.task_description[:30]],
        )
        self._memory_store.store(entry)
        session.observations.append({"type": obs_type, "data": data,
                                    "timestamp": time.time()})

    def _derive_lessons(self, session: LearningSession) -> List[str]:
        lessons = []
        if session.success:
            lessons.append(
                f"Task '{session.task_description[:80]}' completed successfully "
                f"with {len(session.actions_taken)} actions."
            )
            if session.actions_taken:
                actions = [a["action"] for a in session.actions_taken]
                lessons.append(f"Effective action sequence: {' -> '.join(actions)}")
        else:
            lessons.append(
                f"Task '{session.task_description[:80]}' failed. "
                f"Review action sequence for improvement."
            )
            if session.actions_taken:
                last_action = session.actions_taken[-1]
                lessons.append(
                    f"Last action '{last_action['action']}' may need refinement."
                )
        return lessons

    def _generate_skill(self, session: LearningSession) -> Optional[SkillManifest]:
        """Generate a skill from a session if it represents a repeatable pattern."""
        if not session.success or len(session.actions_taken) < 2:
            return None

        # Check if a similar skill already exists
        existing = self._skill_library.find_by_trigger(session.task_description)
        if existing:
            # Update existing skill instead
            existing_skill = existing[0]
            existing_skill.usage_count += 1
            existing_skill.updated_at = time.time()
            existing_skill.version += 1
            return existing_skill

        # Generate new skill
        skill = SkillManifest(
            skill_id=f"skill_{uuid.uuid4().hex[:12]}",
            name=f"auto_{session.task_description[:40].replace(' ', '_')}",
            description=session.task_description[:200],
            trigger_patterns=[
                session.task_description.lower()[:60],
                *[a["action"] for a in session.actions_taken[:3]],
            ],
            steps=[
                {"step": i + 1, "action": a["action"], "params": a["params"]}
                for i, a in enumerate(session.actions_taken)
            ],
            success_rate=1.0,
            usage_count=1,
            lifecycle=SkillLifecycle.DRAFT,
        )

        if self._skill_library.register(skill):
            return skill
        return None

    def get_memory_statistics(self) -> Dict[str, Any]:
        return self._memory_store.get_statistics()

    def get_skill_statistics(self) -> Dict[str, Any]:
        return self._skill_library.get_statistics()

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._active_sessions.values()]

    def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.to_dict()
                   for s in self._session_history[-limit:]]

    def search_memory(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        results = self._memory_store.search(keyword, limit=limit)
        return [r.to_dict() for r in results]

    def get_skills(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._skill_library.get_all_active()]

    def promote_skill(self, skill_id: str) -> bool:
        with self._lock:
            skill = self._skill_library.get(skill_id)
            if skill and skill.lifecycle == SkillLifecycle.DRAFT:
                skill.lifecycle = SkillLifecycle.ACTIVE
                return True
            return False

    def deprecate_skill(self, skill_id: str) -> bool:
        with self._lock:
            skill = self._skill_library.get(skill_id)
            if skill:
                skill.lifecycle = SkillLifecycle.DEPRECATED
                return True
            return False


def get_learning_loop() -> LearningLoopEngine:
    """Get the global LearningLoopEngine instance."""
    return LearningLoopEngine.get_instance()