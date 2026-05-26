"""
SparkLabs Agent - Skill Synthesizer

Autonomous closed learning loop that observes agent execution patterns across
sessions, identifies repeated successful strategies, and crystallizes them
into reusable skill documents. The synthesizer forms the backbone of SparkLabs'
self-improving agent fabric, enabling the engine to grow its own capability
surface without human intervention.

Architecture:
  SkillSynthesizer (Singleton)
    |-- ExecutionPattern (observed strategy repetition)
    |-- SkillDocument (reusable capability blueprint)
    |-- SynthesisSession (observation-to-skill lifecycle)
    |-- SkillCondition (applicability constraints)

Synthesis Cycle:
  OBSERVING -> IDENTIFYING -> GENERATING -> REVIEWING -> PUBLISHED

Usage:
    synth = get_skill_synthesizer()
    synth.observe_trajectory("sess_01", ["tool_a", "tool_b", "tool_c"], True, {})
    patterns = synth.analyze_patterns(min_occurrences=3)
    for pid in patterns:
        skill = synth.synthesize_skill(pid)
    catalog = synth.get_skill_catalog(category=PatternCategory.GAME_LOGIC)
"""

from __future__ import annotations

import json
import math
import random
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_time_module = time


class SynthesisTrigger(Enum):
    PATTERN_REPETITION = "pattern_repetition"
    COMPLEXITY_THRESHOLD = "complexity_threshold"
    TIME_SAVINGS = "time_savings"
    SUCCESS_RATE = "success_rate"
    USER_REQUEST = "user_request"


class SkillMaturity(Enum):
    EMBRYONIC = "embryonic"
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    BATTLE_TESTED = "battle_tested"
    DEPRECATED = "deprecated"


class SynthesisStatus(Enum):
    OBSERVING = "observing"
    IDENTIFYING = "identifying"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    PUBLISHED = "published"
    PATCHED = "patched"


class PatternCategory(Enum):
    GAME_LOGIC = "game_logic"
    LEVEL_DESIGN = "level_design"
    CHARACTER_SETUP = "character_setup"
    DIALOGUE = "dialogue"
    UI_LAYOUT = "ui_layout"
    PERFORMANCE_TUNING = "performance_tuning"
    DEBUGGING = "debugging"
    ASSET_GENERATION = "asset_generation"


_MIN_OCCURRENCES_DEFAULT = 3
_MIN_SUCCESS_RATE_DEFAULT = 0.7
_MAX_TRAJECTORY_WINDOW = 1000
_PATTERN_SIMILARITY_THRESHOLD = 0.55
_MATURITY_USAGE_BASELINE_FOR_STABLE = 25
_MATURITY_USAGE_BASELINE_FOR_BATTLE_TESTED = 100

_TOOL_CATEGORY_MAP: Dict[str, PatternCategory] = {
    "game_coder": PatternCategory.GAME_LOGIC,
    "world_builder": PatternCategory.LEVEL_DESIGN,
    "agent_character_setup": PatternCategory.CHARACTER_SETUP,
    "agent_dialogue": PatternCategory.DIALOGUE,
    "agent_ui_designer": PatternCategory.UI_LAYOUT,
    "agent_performance_advisor": PatternCategory.PERFORMANCE_TUNING,
    "agent_debug_protocol": PatternCategory.DEBUGGING,
    "agent_asset_optimizer": PatternCategory.ASSET_GENERATION,
    "agent_shader_advisor": PatternCategory.ASSET_GENERATION,
    "agent_audio_composer": PatternCategory.ASSET_GENERATION,
}

_STOP_WORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "from", "by", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall", "not",
    "no", "nor", "so", "if", "then", "else", "when", "where", "how",
    "all", "each", "every", "both", "few", "more", "most", "some", "any",
    "this", "that", "these", "those", "it", "its", "we", "us", "our",
}


@dataclass
class ExecutionPattern:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_count: int = 0
    tool_sequence: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    avg_turns: float = 0.0
    description: str = ""
    category: PatternCategory = PatternCategory.GAME_LOGIC
    first_seen: float = field(default_factory=lambda: __import__("time").time())
    last_seen: float = field(default_factory=lambda: __import__("time").time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_count": self.session_count,
            "tool_sequence": list(self.tool_sequence),
            "tool_sequence_hash": self._sequence_hash(),
            "success_rate": round(self.success_rate, 4),
            "avg_turns": round(self.avg_turns, 2),
            "description": self.description,
            "category": self.category.value,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "metadata": dict(self.metadata),
        }

    def _sequence_hash(self) -> str:
        joined = "|".join(sorted(self.tool_sequence))
        return hashlib_sha256_hex(joined)[:12]


@dataclass
class SkillDocument:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    pattern_ref: str = ""
    maturity: SkillMaturity = SkillMaturity.EMBRYONIC
    version: int = 1
    yaml_frontmatter: Dict[str, Any] = field(default_factory=dict)
    body_markdown: str = ""
    created_at: float = field(default_factory=lambda: __import__("time").time())
    updated_at: float = field(default_factory=lambda: __import__("time").time())
    usage_count: int = 0
    deprecates: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pattern_ref": self.pattern_ref,
            "maturity": self.maturity.value,
            "version": self.version,
            "yaml_frontmatter": dict(self.yaml_frontmatter),
            "body_length": len(self.body_markdown),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "deprecates": self.deprecates,
        }


@dataclass
class SynthesisSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: SynthesisStatus = SynthesisStatus.OBSERVING
    patterns_found: int = 0
    skills_generated: int = 0
    skills_patched: int = 0
    start_time: float = field(default_factory=lambda: __import__("time").time())
    end_time: Optional[float] = None
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "patterns_found": self.patterns_found,
            "skills_generated": self.skills_generated,
            "skills_patched": self.skills_patched,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(
                (self.end_time or __import__("time").time()) - self.start_time, 2
            ),
            "stats": dict(self.stats),
        }


@dataclass
class SkillCondition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    requires_toolsets: List[str] = field(default_factory=list)
    fallback_for_toolsets: List[str] = field(default_factory=list)
    requires_tools: List[str] = field(default_factory=list)
    fallback_for_tools: List[str] = field(default_factory=list)
    min_session_count: int = 0
    min_success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "requires_toolsets": list(self.requires_toolsets),
            "fallback_for_toolsets": list(self.fallback_for_toolsets),
            "requires_tools": list(self.requires_tools),
            "fallback_for_tools": list(self.fallback_for_tools),
            "min_session_count": self.min_session_count,
            "min_success_rate": self.min_success_rate,
        }


class SkillSynthesizer:
    """
    Autonomous skill synthesis engine that observes agent execution traces
    across sessions, identifies repeated successful tool-use strategies, and
    crystallizes them into reusable SkillDocuments. The synthesizer runs a
    full closed loop: observe -> identify -> generate -> review -> publish.

    Each ExecutionPattern captures a specific sequence of tool invocations
    that consistently produced successful outcomes. When a pattern reaches
    sufficient repeat evidence, the synthesizer creates a SkillDocument with
    YAML frontmatter and descriptive markdown body. Skills mature over time
    as they accumulate usage across sessions, graduating from EMBRYONIC
    through EXPERIMENTAL and STABLE to BATTLE_TESTED.

    Usage:
        synth = get_skill_synthesizer()
        synth.observe_trajectory("sess_01", ["tool_a", "tool_b", "tool_c"], True, {})
        patterns = synth.analyze_patterns()
        for pid in patterns:
            skill = synth.synthesize_skill(pid)
        synth.run_synthesis_cycle()
    """

    _instance: Optional["SkillSynthesizer"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "SkillSynthesizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SkillSynthesizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._patterns: Dict[str, ExecutionPattern] = {}
        self._skills: Dict[str, SkillDocument] = {}
        self._sessions: Dict[str, SynthesisSession] = {}
        self._conditions: Dict[str, SkillCondition] = {}
        self._trajectories: Dict[str, List[Dict[str, Any]]] = {}
        self._sequence_index: Dict[str, List[str]] = {}
        self._total_trajectories: int = 0
        self._total_successes: int = 0
        self._total_failures: int = 0
        self._total_skills_generated: int = 0
        self._total_skills_patched: int = 0
        self._current_session_id: Optional[str] = None

    def observe_trajectory(
        self,
        session_id: str,
        tool_sequence: List[str],
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if session_id not in self._trajectories:
            self._trajectories[session_id] = []

        trajectory_count = len(self._trajectories[session_id])
        if trajectory_count >= _MAX_TRAJECTORY_WINDOW:
            self._trajectories[session_id].pop(0)

        entry = {
            "tools": list(tool_sequence),
            "success": success,
            "turns": len(tool_sequence),
            "timestamp": _time_module.time(),
            "metadata": dict(metadata or {}),
        }
        self._trajectories[session_id].append(entry)
        self._total_trajectories += 1

        if success:
            self._total_successes += 1
        else:
            self._total_failures += 1

        seq_key = "|".join(tool_sequence)
        if seq_key not in self._sequence_index:
            self._sequence_index[seq_key] = []
        self._sequence_index[seq_key].append(session_id)

        if not self._current_session_id:
            self._current_session_id = uuid.uuid4().hex
            session = SynthesisSession(
                id=self._current_session_id,
                status=SynthesisStatus.OBSERVING,
                start_time=_time_module.time(),
            )
            self._sessions[self._current_session_id] = session

    def analyze_patterns(
        self,
        min_occurrences: int = _MIN_OCCURRENCES_DEFAULT,
        min_success_rate: float = _MIN_SUCCESS_RATE_DEFAULT,
    ) -> List[str]:
        new_pattern_ids: List[str] = []

        for seq_key, session_ids in list(self._sequence_index.items()):
            unique_sessions = set(session_ids)
            if len(unique_sessions) < min_occurrences:
                continue

            tool_list = seq_key.split("|") if seq_key else []
            if len(tool_list) < 2:
                continue

            successful = 0
            total = 0
            total_turns = 0
            aggregated_metadata: Dict[str, Any] = {}

            for sid in unique_sessions:
                if sid not in self._trajectories:
                    continue
                for entry in self._trajectories[sid]:
                    if entry.get("tools") == tool_list or (
                        len(entry.get("tools", [])) == len(tool_list)
                        and all(t in entry.get("tools", []) for t in tool_list)
                    ):
                        total += 1
                        total_turns += entry.get("turns", 0)
                        if entry.get("success"):
                            successful += 1
                        if entry.get("metadata"):
                            aggregated_metadata.update(entry["metadata"])

            if total == 0:
                continue

            success_rate = successful / total
            if success_rate < min_success_rate:
                continue

            existing_id = self._find_similar_pattern(tool_list)
            if existing_id:
                pattern = self._patterns[existing_id]
                pattern.session_count += len(unique_sessions)
                pattern.success_rate = (
                    (pattern.success_rate * (pattern.session_count - len(unique_sessions))
                     + success_rate * len(unique_sessions))
                    / pattern.session_count
                )
                pattern.last_seen = _time_module.time()
                pattern.metadata.update(aggregated_metadata)
                new_pattern_ids.append(existing_id)
                continue

            category = self._infer_category(tool_list)
            description = self._generate_pattern_description(tool_list, category, success_rate)

            pattern = ExecutionPattern(
                session_count=len(unique_sessions),
                tool_sequence=list(tool_list),
                success_rate=success_rate,
                avg_turns=total_turns / total,
                description=description,
                category=category,
                metadata=aggregated_metadata,
            )
            self._patterns[pattern.id] = pattern
            new_pattern_ids.append(pattern.id)

        if self._current_session_id:
            session = self._sessions.get(self._current_session_id)
            if session:
                session.status = SynthesisStatus.IDENTIFYING
                session.patterns_found = len(new_pattern_ids)

        return new_pattern_ids

    def synthesize_skill(self, pattern_id: str) -> Optional[SkillDocument]:
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            return None

        condition_id = uuid.uuid4().hex
        condition = SkillCondition(
            id=condition_id,
            requires_tools=list(pattern.tool_sequence),
            min_session_count=max(1, pattern.session_count // 2),
            min_success_rate=max(0.5, pattern.success_rate - 0.1),
        )
        self._conditions[condition_id] = condition

        name = self._generate_skill_name(pattern)
        yaml_frontmatter = {
            "skill_name": name,
            "category": pattern.category.value,
            "maturity": SkillMaturity.EMBRYONIC.value,
            "version": 1,
            "pattern_ref": pattern_id,
            "condition_ref": condition_id,
            "success_rate": round(pattern.success_rate, 4),
            "session_count": pattern.session_count,
            "avg_turns": round(pattern.avg_turns, 2),
            "tools": list(pattern.tool_sequence),
            "generated_by": "sparklabs_skill_synthesizer",
            "auto_published": True,
        }

        body = self._generate_skill_body(pattern, name)

        skill = SkillDocument(
            name=name,
            description=pattern.description,
            pattern_ref=pattern_id,
            yaml_frontmatter=yaml_frontmatter,
            body_markdown=body,
        )
        self._skills[skill.id] = skill
        self._total_skills_generated += 1

        if self._current_session_id:
            session = self._sessions.get(self._current_session_id)
            if session:
                session.status = SynthesisStatus.GENERATING
                session.skills_generated += 1

        return skill

    def patch_skill(
        self,
        skill_id: str,
        updated_description: str,
        updated_body: str,
    ) -> Optional[SkillDocument]:
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        skill.description = updated_description
        skill.body_markdown = updated_body
        skill.updated_at = _time_module.time()
        skill.version += 1
        self._total_skills_patched += 1

        if self._current_session_id:
            session = self._sessions.get(self._current_session_id)
            if session:
                session.skills_patched += 1

        return skill

    def evaluate_maturity(self, skill_id: str) -> SkillMaturity:
        skill = self._skills.get(skill_id)
        if skill is None:
            return SkillMaturity.EMBRYONIC

        if skill.maturity == SkillMaturity.DEPRECATED:
            return SkillMaturity.DEPRECATED

        age_days = (_time_module.time() - skill.created_at) / 86400.0

        if skill.usage_count >= _MATURITY_USAGE_BASELINE_FOR_BATTLE_TESTED and age_days >= 30:
            skill.maturity = SkillMaturity.BATTLE_TESTED
        elif skill.usage_count >= _MATURITY_USAGE_BASELINE_FOR_STABLE and age_days >= 7:
            skill.maturity = SkillMaturity.STABLE
        elif skill.usage_count >= 10 and age_days >= 1:
            skill.maturity = SkillMaturity.EXPERIMENTAL

        return skill.maturity

    def get_skill_catalog(
        self,
        category: Optional[PatternCategory] = None,
        min_maturity: Optional[SkillMaturity] = None,
    ) -> List[Dict[str, Any]]:
        maturity_order: Dict[SkillMaturity, int] = {
            SkillMaturity.EMBRYONIC: 0,
            SkillMaturity.EXPERIMENTAL: 1,
            SkillMaturity.STABLE: 2,
            SkillMaturity.BATTLE_TESTED: 3,
            SkillMaturity.DEPRECATED: 4,
        }

        results: List[Dict[str, Any]] = []

        for skill in self._skills.values():
            if skill.maturity == SkillMaturity.DEPRECATED:
                continue

            if category is not None:
                pattern = self._patterns.get(skill.pattern_ref)
                if pattern is None or pattern.category != category:
                    continue

            if min_maturity is not None:
                if maturity_order.get(skill.maturity, 0) < maturity_order.get(min_maturity, 0):
                    continue

            entry = skill.to_dict()

            pattern = self._patterns.get(skill.pattern_ref)
            if pattern:
                entry["category"] = pattern.category.value
                entry["success_rate"] = round(pattern.success_rate, 4)
                entry["session_count"] = pattern.session_count

            entry["maturity_order"] = maturity_order.get(skill.maturity, 0)
            results.append(entry)

        results.sort(key=lambda r: (-r.get("maturity_order", 0), -r.get("usage_count", 0)))
        return results

    def export_skill(self, skill_id: str) -> Optional[str]:
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        yaml_lines = ["---"]
        for key, value in skill.yaml_frontmatter.items():
            if isinstance(value, list):
                yaml_lines.append(f"{key}:")
                for item in value:
                    yaml_lines.append(f"  - {item}")
            else:
                yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")

        frontmatter = "\n".join(yaml_lines)
        return f"{frontmatter}\n\n{skill.body_markdown}"

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored: List[Tuple[float, Dict[str, Any]]] = []

        for skill_id, skill in self._skills.items():
            if skill.maturity == SkillMaturity.DEPRECATED:
                continue

            description_tokens = self._tokenize(skill.description)
            name_tokens = self._tokenize(skill.name)
            body_tokens = self._tokenize(skill.body_markdown)

            desc_score = self._jaccard_similarity(query_tokens, description_tokens)
            name_score = self._jaccard_similarity(query_tokens, name_tokens) * 2.0
            body_score = self._jaccard_similarity(query_tokens, body_tokens) * 0.5

            combined = desc_score + name_score + body_score
            if combined > 0.05:
                scored.append((combined, skill.to_dict()))

        scored.sort(key=lambda x: -x[0])
        return [entry for _, entry in scored[:20]]

    def deprecate_skill(
        self,
        skill_id: str,
        replacement_id: Optional[str] = None,
    ) -> bool:
        skill = self._skills.get(skill_id)
        if skill is None:
            return False

        skill.maturity = SkillMaturity.DEPRECATED
        if replacement_id:
            skill.deprecates = replacement_id
        skill.updated_at = _time_module.time()
        return True

    def get_synthesis_stats(self) -> Dict[str, Any]:
        total_skills = len(self._skills)
        deprecated_count = sum(
            1 for s in self._skills.values()
            if s.maturity == SkillMaturity.DEPRECATED
        )
        active_skills = total_skills - deprecated_count

        category_counts: Dict[str, int] = {}
        for skill in self._skills.values():
            if skill.maturity == SkillMaturity.DEPRECATED:
                continue
            pattern = self._patterns.get(skill.pattern_ref)
            cat = pattern.category.value if pattern else "unknown"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        maturity_counts: Dict[str, int] = {}
        for skill in self._skills.values():
            mat = skill.maturity.value
            maturity_counts[mat] = maturity_counts.get(mat, 0) + 1

        return {
            "total_trajectories": self._total_trajectories,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "success_rate": round(
                self._total_successes / max(1, self._total_trajectories), 4
            ),
            "total_patterns": len(self._patterns),
            "total_skills": total_skills,
            "active_skills": active_skills,
            "deprecated_skills": deprecated_count,
            "total_skills_generated": self._total_skills_generated,
            "total_skills_patched": self._total_skills_patched,
            "categories": category_counts,
            "maturities": maturity_counts,
            "sessions_tracked": len(self._trajectories),
            "sequence_index_size": len(self._sequence_index),
            "current_session_id": self._current_session_id,
        }

    def run_synthesis_cycle(self) -> Dict[str, Any]:
        session = SynthesisSession(
            status=SynthesisStatus.OBSERVING,
            start_time=_time_module.time(),
        )
        self._sessions[session.id] = session
        self._current_session_id = session.id

        session.status = SynthesisStatus.IDENTIFYING
        pattern_ids = self.analyze_patterns()
        session.patterns_found = len(pattern_ids)

        session.status = SynthesisStatus.GENERATING
        skill_ids: List[str] = []
        for pid in pattern_ids:
            skill = self.synthesize_skill(pid)
            if skill:
                skill_ids.append(skill.id)
        session.skills_generated = len(skill_ids)

        session.status = SynthesisStatus.REVIEWING
        for sid in skill_ids:
            self.evaluate_maturity(sid)

        session.status = SynthesisStatus.PUBLISHED
        session.end_time = _time_module.time()

        session_stats = {
            "patterns_found": session.patterns_found,
            "skills_generated": session.skills_generated,
            "skills_patched": session.skills_patched,
            "duration_seconds": round(session.end_time - session.start_time, 2),
        }
        session.stats = session_stats

        return {
            "session_id": session.id,
            "status": session.status.value,
            "pattern_ids": pattern_ids,
            "skill_ids": skill_ids,
            "stats": session_stats,
        }

    def _find_similar_pattern(self, tool_sequence: List[str]) -> Optional[str]:
        query_set = set(tool_sequence)
        for pattern_id, pattern in self._patterns.items():
            existing_set = set(pattern.tool_sequence)
            if not query_set or not existing_set:
                continue
            intersection = query_set & existing_set
            union = query_set | existing_set
            jaccard = len(intersection) / len(union)
            if jaccard >= _PATTERN_SIMILARITY_THRESHOLD and len(tool_sequence) == len(
                pattern.tool_sequence
            ):
                return pattern_id
        return None

    def _infer_category(self, tool_sequence: List[str]) -> PatternCategory:
        category_votes: Dict[PatternCategory, int] = {}
        for tool in tool_sequence:
            for key, cat in _TOOL_CATEGORY_MAP.items():
                if key in tool.lower():
                    category_votes[cat] = category_votes.get(cat, 0) + 1
        if category_votes:
            return max(category_votes, key=lambda k: category_votes[k])
        return PatternCategory.GAME_LOGIC

    def _generate_pattern_description(
        self,
        tool_sequence: List[str],
        category: PatternCategory,
        success_rate: float,
    ) -> str:
        unique_tools = list(dict.fromkeys(tool_sequence))
        tool_names = ", ".join(unique_tools[:5])
        if len(unique_tools) > 5:
            tool_names += f" and {len(unique_tools) - 5} more"

        category_label = category.value.replace("_", " ").title()
        return (
            f"SparkLabs synthesized {category_label} pattern using {tool_names}. "
            f"Observed across sessions with {success_rate:.0%} success rate "
            f"over {len(tool_sequence)} turns per execution."
        )

    def _generate_skill_name(self, pattern: ExecutionPattern) -> str:
        category_prefix = pattern.category.value.replace("_", " ").title().replace(" ", "")
        tool_count = len(pattern.tool_sequence)
        return f"{category_prefix}_Skill_{tool_count}Tool_{pattern.id[:8]}"

    def _generate_skill_body(self, pattern: ExecutionPattern, name: str) -> str:
        lines: List[str] = []
        lines.append(f"# {name}")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(pattern.description)
        lines.append("")
        lines.append("## Tool Sequence")
        lines.append("")
        for i, tool in enumerate(pattern.tool_sequence, start=1):
            lines.append(f"{i}. `{tool}`")
        lines.append("")
        lines.append("## Performance Metrics")
        lines.append("")
        lines.append(f"- **Success Rate**: {pattern.success_rate:.2%}")
        lines.append(f"- **Sessions Observed**: {pattern.session_count}")
        lines.append(f"- **Average Turns**: {pattern.avg_turns:.2f}")
        lines.append(f"- **Category**: {pattern.category.value}")
        lines.append("")
        lines.append("## Usage Guidance")
        lines.append("")
        lines.append(
            "This skill was autonomously synthesized by the SparkLabs Skill "
            "Synthesizer after observing repeated successful execution patterns "
            "across multiple agent sessions. Apply this skill when the tool "
            "sequence matches the context of the current task."
        )
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            "*Generated by SparkLabs Skill Synthesizer. Review and refine "
            "before production use.*"
        )
        return "\n".join(lines)

    def _tokenize(self, text: str) -> Set[str]:
        words = re.findall(r"[a-z0-9_]+", text.lower())
        return {w for w in words if w not in _STOP_WORDS and len(w) > 1}

    def _jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_patterns": len(self._patterns),
            "total_skills": len(self._skills),
            "catalog_size": sum(
                1 for s in self._skills.values()
                if s.maturity != SkillMaturity.DEPRECATED
            ),
            "sessions_completed": len(self._sessions),
        }


def hashlib_sha256_hex(data: str) -> str:
    try:
        import hashlib
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    except Exception:
        return hex(abs(hash(data)))[2:][:12]


def get_skill_synthesizer() -> SkillSynthesizer:
    return SkillSynthesizer.get_instance()