"""
SparkAI Agent - Skill Curator

Autonomous skill lifecycle management system. Periodically reviews
agent-created game skills, detects staleness, triggers archival,
and orchestrates background review/consolidation operations.

The curator runs as a background process within the agent runtime,
maintaining persistent state through a dotfile-based registry.
It supports consolidation strategies that merge overlapping skills
and provides detailed reports on skill ecosystem health.

Architecture:
  SkillCurator
    |-- SkillRegistry (persistent skill tracking)
    |-- ReviewScheduler (interval-based review triggers)
    |-- ConsolidationEngine (skill merging/dedup)
    |-- StalenessDetector (inactivity-based decay)
    |-- ReportGenerator (ecosystem health reports)

Lifecycle States:
  active -> stale (after inactivity window)
  stale -> archived (after extended inactivity)
  archived -> re-activated (on manual restore)
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SkillLifecycle(Enum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"
    UNDER_REVIEW = "under_review"
    CONSOLIDATED = "consolidated"
    DEPRECATED = "deprecated"


class ConsolidationStrategy(Enum):
    MERGE = "merge"
    REPLACE = "replace"
    KEEP_SEPARATE = "keep_separate"
    DISCARD = "discard"


@dataclass
class SkillEntry:
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    name: str = ""
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)

    lifecycle: SkillLifecycle = SkillLifecycle.ACTIVE
    version: int = 1
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    created_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None
    last_reviewed_at: Optional[float] = None

    source_agent: str = ""
    consolidation_parent: Optional[str] = None
    merged_from: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.usage_count
        if total == 0:
            return 1.0
        return self.success_count / total

    @property
    def days_since_use(self) -> float:
        if not self.last_used_at:
            return (time.time() - self.created_at) / 86400.0
        return (time.time() - self.last_used_at) / 86400.0

    @property
    def days_since_review(self) -> float:
        if not self.last_reviewed_at:
            return self.days_since_use
        return (time.time() - self.last_reviewed_at) / 86400.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "lifecycle": self.lifecycle.value,
            "version": self.version,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 3),
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "last_reviewed_at": self.last_reviewed_at,
            "source_agent": self.source_agent,
            "consolidation_parent": self.consolidation_parent,
            "merged_from": self.merged_from,
            "days_since_use": round(self.days_since_use, 1),
            "days_since_review": round(self.days_since_review, 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillEntry:
        entry = cls(
            skill_id=data.get("skill_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            tags=data.get("tags", []),
        )
        entry.lifecycle = SkillLifecycle(data.get("lifecycle", "active"))
        entry.version = data.get("version", 1)
        entry.usage_count = data.get("usage_count", 0)
        entry.success_count = data.get("success_count", 0)
        entry.failure_count = data.get("failure_count", 0)
        entry.created_at = data.get("created_at", time.time())
        entry.last_used_at = data.get("last_used_at")
        entry.last_reviewed_at = data.get("last_reviewed_at")
        entry.source_agent = data.get("source_agent", "")
        entry.consolidation_parent = data.get("consolidation_parent")
        entry.merged_from = data.get("merged_from", [])
        entry.metadata = data.get("metadata", {})
        return entry


@dataclass
class CuratorConfig:
    review_interval_hours: float = 24.0
    staleness_threshold_days: float = 14.0
    archival_threshold_days: float = 60.0
    max_skills_per_review: int = 5
    auto_archive: bool = True
    consolidation_enabled: bool = True
    similarity_threshold: float = 0.7
    state_file_path: str = ".sparklabs_curator_state"
    emit_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None


def _compute_text_similarity(a: str, b: str) -> float:
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0.0
    intersection = a_words & b_words
    union = a_words | b_words
    return len(intersection) / len(union)


class SkillCurator:
    """
    Autonomous skill lifecycle manager.

    Monitors all registered game skills, detects staleness based on
    usage patterns, triggers automatic archival, and orchestrates
    consolidation when similar skills emerge. Runs as a background
    task within the agent runtime.

    The curator maintains a persistent state file that survives
    agent restarts, enabling long-term skill ecosystem tracking
    across multiple sessions.

    Usage:
        curator = SkillCurator(config=CuratorConfig())
        curator.register_skill(
            name="AI World Builder",
            description="Generates procedural terrain using neural networks",
            category="world",
            source_agent="orchestrator"
        )
        review_result = await curator.review()
    """

    def __init__(self, config: Optional[CuratorConfig] = None):
        self._config = config or CuratorConfig()
        self._skills: Dict[str, SkillEntry] = {}
        self._review_history: List[Dict[str, Any]] = []
        self._last_review_time: float = 0.0
        self._consolidation_log: List[Dict[str, Any]] = []
        self._load_state()

    def _load_state(self) -> None:
        path = self._config.state_file_path
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for entry_data in data.get("skills", []):
                entry = SkillEntry.from_dict(entry_data)
                self._skills[entry.skill_id] = entry
            self._last_review_time = data.get("last_review_time", 0.0)
            self._review_history = data.get("review_history", [])
            self._consolidation_log = data.get("consolidation_log", [])
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    def _save_state(self) -> None:
        try:
            data = {
                "skills": [e.to_dict() for e in self._skills.values()],
                "last_review_time": self._last_review_time,
                "review_history": self._review_history[-100:],
                "consolidation_log": self._consolidation_log[-100:],
                "saved_at": time.time(),
            }
            with open(self._config.state_file_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        if self._config.emit_callback:
            self._config.emit_callback(event, data)

    def register_skill(
        self,
        name: str,
        description: str,
        category: str,
        source_agent: str = "",
        tags: Optional[List[str]] = None,
    ) -> SkillEntry:
        for existing in self._skills.values():
            if existing.name.lower() == name.lower() and existing.category == category:
                existing.version += 1
                existing.description = description
                existing.tags = tags or existing.tags
                existing.last_used_at = time.time()
                existing.usage_count += 1
                self._save_state()
                self._emit("skill_updated", {"skill_id": existing.skill_id, "name": name})
                return existing

        entry = SkillEntry(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            source_agent=source_agent,
        )
        self._skills[entry.skill_id] = entry
        self._save_state()
        self._emit("skill_registered", {"skill_id": entry.skill_id, "name": name, "category": category})
        return entry

    def record_usage(self, skill_id: str, success: bool = True) -> None:
        entry = self._skills.get(skill_id)
        if not entry:
            return
        entry.usage_count += 1
        entry.last_used_at = time.time()
        if success:
            entry.success_count += 1
        else:
            entry.failure_count += 1
        self._save_state()

    def detect_staleness(self) -> List[SkillEntry]:
        stale = []
        for entry in self._skills.values():
            if entry.lifecycle not in (SkillLifecycle.ACTIVE, SkillLifecycle.UNDER_REVIEW):
                continue
            if entry.days_since_use >= self._config.staleness_threshold_days:
                stale.append(entry)
        return stale

    def detect_archivable(self) -> List[SkillEntry]:
        archivable = []
        for entry in self._skills.values():
            if entry.lifecycle != SkillLifecycle.STALE:
                continue
            if entry.days_since_use >= self._config.archival_threshold_days:
                archivable.append(entry)
        return archivable

    def detect_duplicates(self) -> List[Tuple[SkillEntry, SkillEntry, float]]:
        pairs = []
        entries = list(self._skills.values())
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                a, b = entries[i], entries[j]
                if a.category != b.category:
                    continue
                if a.lifecycle in (SkillLifecycle.ARCHIVED, SkillLifecycle.DEPRECATED):
                    continue
                if b.lifecycle in (SkillLifecycle.ARCHIVED, SkillLifecycle.DEPRECATED):
                    continue
                similarity = _compute_text_similarity(a.description, b.description)
                if similarity >= self._config.similarity_threshold:
                    pairs.append((a, b, similarity))
        return sorted(pairs, key=lambda x: x[2], reverse=True)

    def mark_stale(self, skill_id: str, reason: str = "") -> None:
        entry = self._skills.get(skill_id)
        if not entry:
            return
        entry.lifecycle = SkillLifecycle.STALE
        entry.metadata["stale_reason"] = reason
        entry.metadata["stale_at"] = time.time()
        self._save_state()
        self._emit("skill_stale", {"skill_id": skill_id, "name": entry.name, "reason": reason})

    def mark_archived(self, skill_id: str) -> None:
        entry = self._skills.get(skill_id)
        if not entry:
            return
        entry.lifecycle = SkillLifecycle.ARCHIVED
        entry.metadata["archived_at"] = time.time()
        self._save_state()
        self._emit("skill_archived", {"skill_id": skill_id, "name": entry.name})

    def mark_reviewed(self, skill_id: str) -> None:
        entry = self._skills.get(skill_id)
        if not entry:
            return
        entry.last_reviewed_at = time.time()

    def consolidate(
        self,
        parent_id: str,
        child_ids: List[str],
        strategy: ConsolidationStrategy = ConsolidationStrategy.MERGE,
    ) -> Optional[SkillEntry]:
        parent = self._skills.get(parent_id)
        if not parent:
            return None

        children = []
        for cid in child_ids:
            child = self._skills.get(cid)
            if child and child.skill_id != parent_id:
                children.append(child)

        if not children:
            return parent

        if strategy == ConsolidationStrategy.MERGE:
            all_tags = list(set(parent.tags))
            for child in children:
                all_tags.extend(child.tags)
                child.lifecycle = SkillLifecycle.CONSOLIDATED
                child.consolidation_parent = parent_id
                parent.merged_from.append(child.skill_id)
                parent.usage_count += child.usage_count
                parent.success_count += child.success_count
            parent.tags = list(set(all_tags))
            parent.version += 1

        elif strategy == ConsolidationStrategy.REPLACE:
            for child in children:
                child.lifecycle = SkillLifecycle.DEPRECATED
                child.consolidation_parent = parent_id

        self._consolidation_log.append({
            "timestamp": time.time(),
            "strategy": strategy.value,
            "parent_id": parent_id,
            "child_ids": child_ids,
            "parent_name": parent.name,
        })
        self._save_state()
        self._emit("skill_consolidated", {
            "parent_id": parent_id,
            "child_ids": child_ids,
            "strategy": strategy.value,
        })
        return parent

    async def review(self, llm_provider: Optional[Any] = None) -> Dict[str, Any]:
        now = time.time()
        hours_since_last = (now - self._last_review_time) / 3600.0
        if hours_since_last < self._config.review_interval_hours and self._last_review_time > 0:
            return {"status": "skipped", "reason": f"Next review in {self._config.review_interval_hours - hours_since_last:.1f}h"}

        stale = self.detect_staleness()
        for entry in stale[:self._config.max_skills_per_review]:
            self.mark_stale(entry.skill_id, f"Unused for {entry.days_since_use:.0f} days")
            self.mark_reviewed(entry.skill_id)

        if self._config.auto_archive:
            archivable = self.detect_archivable()
            for entry in archivable:
                self.mark_archived(entry.skill_id)

        duplicates = []
        if self._config.consolidation_enabled:
            duplicates = self.detect_duplicates()

        self._last_review_time = now

        report = {
            "timestamp": now,
            "total_skills": len(self._skills),
            "stale_detected": len(stale),
            "archived": len(self.detect_archivable()),
            "duplicates_found": len(duplicates),
            "active_count": sum(1 for e in self._skills.values() if e.lifecycle == SkillLifecycle.ACTIVE),
            "stale_count": sum(1 for e in self._skills.values() if e.lifecycle == SkillLifecycle.STALE),
            "archived_count": sum(1 for e in self._skills.values() if e.lifecycle == SkillLifecycle.ARCHIVED),
            "consolidated_count": sum(1 for e in self._skills.values() if e.lifecycle == SkillLifecycle.CONSOLIDATED),
        }

        self._review_history.append(report)
        self._save_state()
        self._emit("review_complete", report)
        return {"status": "completed", "report": report}

    def get_skill(self, skill_id: str) -> Optional[SkillEntry]:
        return self._skills.get(skill_id)

    def list_skills(
        self,
        category: Optional[str] = None,
        lifecycle: Optional[SkillLifecycle] = None,
        min_success_rate: float = 0.0,
    ) -> List[SkillEntry]:
        results = list(self._skills.values())
        if category:
            results = [e for e in results if e.category == category]
        if lifecycle:
            results = [e for e in results if e.lifecycle == lifecycle]
        if min_success_rate > 0.0:
            results = [e for e in results if e.success_rate >= min_success_rate]
        return sorted(results, key=lambda e: e.usage_count, reverse=True)

    def get_categories(self) -> List[str]:
        cats: Set[str] = set()
        for entry in self._skills.values():
            if entry.category:
                cats.add(entry.category)
        return sorted(cats)

    def get_ecosystem_health(self) -> Dict[str, Any]:
        total = len(self._skills) or 1
        active = sum(1 for e in self._skills.values() if e.lifecycle == SkillLifecycle.ACTIVE)
        avg_success = 0.0
        success_rates = [e.success_rate for e in self._skills.values() if e.usage_count > 0]
        if success_rates:
            avg_success = sum(success_rates) / len(success_rates)

        category_counts: Dict[str, int] = {}
        for entry in self._skills.values():
            category_counts[entry.category] = category_counts.get(entry.category, 0) + 1

        return {
            "total_skills": len(self._skills),
            "active_ratio": round(active / total, 3),
            "average_success_rate": round(avg_success, 3),
            "stale_count": sum(1 for e in self._skills.values() if e.lifecycle == SkillLifecycle.STALE),
            "archived_count": sum(1 for e in self._skills.values() if e.lifecycle == SkillLifecycle.ARCHIVED),
            "consolidation_count": len(self._consolidation_log),
            "last_review": self._last_review_time,
            "categories": category_counts,
            "total_usage": sum(e.usage_count for e in self._skills.values()),
        }

    def get_review_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._review_history[-limit:]

    def get_consolidation_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._consolidation_log[-limit:]

    def reset(self) -> None:
        self._skills.clear()
        self._review_history.clear()
        self._consolidation_log.clear()
        self._last_review_time = 0.0
        if os.path.exists(self._config.state_file_path):
            os.remove(self._config.state_file_path)


_global_curator: Optional[SkillCurator] = None


def get_skill_curator() -> SkillCurator:
    global _global_curator
    if _global_curator is None:
        _global_curator = SkillCurator()
    return _global_curator
