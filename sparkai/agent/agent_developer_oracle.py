"""
SparkLabs Agent - Developer Oracle

A singleton system that builds a deepening model of the game developer
across sessions. Tracks developer skills, preferences, coding patterns,
tool usage habits, and project context to personalize the AI-native
game development experience.

Architecture:
  DeveloperOracle (singleton)
    |-- DevProfile (per-developer identity, expertise, preferences)
    |-- SessionFootprint (per-session behavioral trace)
    |-- DevInsight (derived observations with confidence scoring)
    |-- Pattern Analyzer (extracts habits from footprint history)
    |-- Recommendation Engine (tool shortcuts, learning paths)
    |-- Action Predictor (next-action inference from context)
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


class DevExpertise(Enum):
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class DevRole(Enum):
    SOLO_DEV = "solo_dev"
    GAME_DESIGNER = "game_designer"
    PROGRAMMER = "programmer"
    ARTIST = "artist"
    PRODUCER = "producer"
    FULL_TEAM = "full_team"


class ProjectPhase(Enum):
    IDEATION = "ideation"
    PROTOTYPING = "prototyping"
    PRODUCTION = "production"
    POLISHING = "polishing"
    SHIPPING = "shipping"
    POST_LAUNCH = "post_launch"


class InteractionPattern(Enum):
    CODE_HEAVY = "code_heavy"
    DESIGN_HEAVY = "design_heavy"
    BALANCED = "balanced"
    EXPLORATORY = "exploratory"
    DEBUGGING = "debugging"


@dataclass
class DevProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: DevRole = DevRole.SOLO_DEV
    expertise: DevExpertise = DevExpertise.NOVICE
    preferred_language: str = "python"
    tool_frequency: Dict[str, int] = field(default_factory=dict)
    session_count: int = 0
    active_hours: List[int] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "expertise": self.expertise.value,
            "preferred_language": self.preferred_language,
            "tool_frequency": dict(self.tool_frequency),
            "session_count": self.session_count,
            "active_hours": list(self.active_hours),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def primary_active_window(self) -> Tuple[int, int]:
        if not self.active_hours:
            return (9, 17)
        hour_counts: Dict[int, int] = {}
        for h in self.active_hours:
            hour_counts[h] = hour_counts.get(h, 0) + 1
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        best = sorted_hours[0][0]
        return (max(0, best - 4), min(23, best + 4))

    def top_tools(self, limit: int = 5) -> List[Tuple[str, int]]:
        sorted_tools = sorted(
            self.tool_frequency.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_tools[:limit]


@dataclass
class SessionFootprint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    tools_used: List[str] = field(default_factory=list)
    commands_issued: int = 0
    code_snippets_created: int = 0
    errors_encountered: int = 0
    duration_minutes: float = 0.0
    complexity_score: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "tools_used": list(self.tools_used),
            "commands_issued": self.commands_issued,
            "code_snippets_created": self.code_snippets_created,
            "errors_encountered": self.errors_encountered,
            "duration_minutes": self.duration_minutes,
            "complexity_score": self.complexity_score,
            "timestamp": self.timestamp,
        }

    def error_rate(self) -> float:
        if self.commands_issued == 0:
            return 0.0
        return self.errors_encountered / max(self.commands_issued, 1)

    def productivity_score(self) -> float:
        if self.duration_minutes <= 0:
            return 0.0
        throughput = (self.commands_issued + self.code_snippets_created) / self.duration_minutes
        return round(throughput * (1.0 - self.error_rate()) * (1.0 + self.complexity_score), 3)


@dataclass
class DevInsight:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    insight_type: str = ""
    description: str = ""
    confidence: float = 0.0
    derived_from_sessions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "insight_type": self.insight_type,
            "description": self.description,
            "confidence": self.confidence,
            "derived_from_sessions": list(self.derived_from_sessions),
            "created_at": self.created_at,
        }


class DeveloperOracle:
    """
    Singleton oracle that models the game developer across sessions.

    Maintains per-developer profiles, session footprints, and derived
    insights. Uses these to personalize tooling, predict next actions,
    and recommend learning resources within the SparkLabs environment.
    """

    _instance: Optional[DeveloperOracle] = None
    _lock = threading.RLock()

    def __new__(cls) -> DeveloperOracle:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> DeveloperOracle:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._profiles: Dict[str, DevProfile] = {}
            self._footprints: Dict[str, SessionFootprint] = {}
            self._insights: Dict[str, DevInsight] = {}
            self._footprint_index: Dict[str, List[str]] = {}
            self._tool_aliases: Dict[str, str] = {
                "code_gen": "code_generation",
                "asset_mgmt": "asset_management",
                "debug": "debugging",
                "design": "game_design",
                "build": "build_system",
                "test": "testing",
                "docs": "documentation",
                "review": "code_review",
                "perf": "performance",
                "refactor": "refactoring",
            }
            self._interaction_history: List[Dict[str, Any]] = []
            self._max_history: int = 500
            self._initialized = True

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        role: DevRole = DevRole.SOLO_DEV,
        expertise: DevExpertise = DevExpertise.NOVICE,
        preferred_language: str = "python",
    ) -> DevProfile:
        with self._lock:
            profile = DevProfile(
                name=name,
                role=role,
                expertise=expertise,
                preferred_language=preferred_language,
            )
            self._profiles[profile.id] = profile
            return profile

    def get_profile(self, profile_id: str) -> Optional[DevProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[DevProfile]:
        return list(self._profiles.values())

    def update_profile(
        self,
        profile_id: str,
        name: Optional[str] = None,
        role: Optional[DevRole] = None,
        expertise: Optional[DevExpertise] = None,
        preferred_language: Optional[str] = None,
    ) -> Optional[DevProfile]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            if name is not None:
                profile.name = name
            if role is not None:
                profile.role = role
            if expertise is not None:
                profile.expertise = expertise
            if preferred_language is not None:
                profile.preferred_language = preferred_language
            profile.updated_at = _time_module.time()
            return profile

    def delete_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id in self._profiles:
                del self._profiles[profile_id]
                self._footprint_index.pop(profile_id, None)
                to_remove = [
                    fid
                    for fid, fp in self._footprints.items()
                    if fp.session_id.startswith(profile_id)
                ]
                for fid in to_remove:
                    del self._footprints[fid]
                insight_to_remove = [
                    iid
                    for iid, ins in self._insights.items()
                    if profile_id in ins.derived_from_sessions
                ]
                for iid in insight_to_remove:
                    del self._insights[iid]
                return True
            return False

    # ------------------------------------------------------------------
    # Session Footprint Recording
    # ------------------------------------------------------------------

    def record_session_footprint(
        self,
        session_id: str,
        tools_used: Optional[List[str]] = None,
        commands_issued: int = 0,
        code_snippets_created: int = 0,
        errors_encountered: int = 0,
        duration_minutes: float = 0.0,
        profile_id: Optional[str] = None,
    ) -> SessionFootprint:
        with self._lock:
            normalized_tools = [self._normalize_tool_name(t) for t in (tools_used or [])]
            complexity = self._compute_complexity(
                commands_issued, code_snippets_created, errors_encountered, duration_minutes
            )
            footprint = SessionFootprint(
                session_id=session_id,
                tools_used=normalized_tools,
                commands_issued=commands_issued,
                code_snippets_created=code_snippets_created,
                errors_encountered=errors_encountered,
                duration_minutes=duration_minutes,
                complexity_score=complexity,
            )
            self._footprints[footprint.id] = footprint

            if profile_id is not None and profile_id in self._profiles:
                self._index_footprint(profile_id, footprint.id)
                self._update_profile_from_footprint(profile_id, footprint)

            self._record_interaction(session_id, footprint)
            return footprint

    def get_session_footprint(self, footprint_id: str) -> Optional[SessionFootprint]:
        return self._footprints.get(footprint_id)

    def list_footprints(self, profile_id: Optional[str] = None) -> List[SessionFootprint]:
        if profile_id is None:
            return list(self._footprints.values())
        indexed = self._footprint_index.get(profile_id, [])
        return [self._footprints[fid] for fid in indexed if fid in self._footprints]

    # ------------------------------------------------------------------
    # Insight Generation
    # ------------------------------------------------------------------

    def analyze_patterns(self, profile_id: Optional[str] = None) -> List[DevInsight]:
        with self._lock:
            footprints = self.list_footprints(profile_id)
            if len(footprints) < 2:
                return []
            insights: List[DevInsight] = []

            insights.extend(self._derive_tool_insights(footprints))
            insights.extend(self._derive_productivity_insights(footprints))
            insights.extend(self._derive_error_insights(footprints))
            insights.extend(self._derive_session_insights(footprints))
            insights.extend(self._derive_language_insights(footprints))

            for ins in insights:
                self._insights[ins.id] = ins

            return insights

    def get_insights(
        self, insight_type: Optional[str] = None, min_confidence: float = 0.0
    ) -> List[DevInsight]:
        results = list(self._insights.values())
        if insight_type is not None:
            results = [i for i in results if i.insight_type == insight_type]
        results = [i for i in results if i.confidence >= min_confidence]
        return sorted(results, key=lambda i: i.confidence, reverse=True)

    def get_latest_insights(self, limit: int = 5) -> List[DevInsight]:
        sorted_insights = sorted(
            self._insights.values(), key=lambda i: i.created_at, reverse=True
        )
        return sorted_insights[:limit]

    # ------------------------------------------------------------------
    # Developer Model
    # ------------------------------------------------------------------

    def get_developer_model(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            profiles = [self._profiles[profile_id]] if profile_id and profile_id in self._profiles else list(self._profiles.values())
            footprints = self.list_footprints(profile_id)

            all_tools: Dict[str, int] = {}
            total_commands = 0
            total_snippets = 0
            total_errors = 0
            total_duration = 0.0
            all_hours: List[int] = []

            for fp in footprints:
                for tool in fp.tools_used:
                    all_tools[tool] = all_tools.get(tool, 0) + 1
                total_commands += fp.commands_issued
                total_snippets += fp.code_snippets_created
                total_errors += fp.errors_encountered
                total_duration += fp.duration_minutes

            for p in profiles:
                all_hours.extend(p.active_hours)

            peak_hours = self._compute_peak_hours(all_hours)
            dominant_pattern = self._compute_interaction_pattern(footprints)

            avg_complexity = 0.0
            if footprints:
                avg_complexity = sum(fp.complexity_score for fp in footprints) / len(footprints)

            error_rate = total_errors / max(total_commands, 1)
            productivity = 0.0
            if total_duration > 0:
                productivity = (total_commands + total_snippets) / total_duration

            return {
                "profile_count": len(profiles),
                "total_sessions": len(footprints),
                "total_commands": total_commands,
                "total_snippets": total_snippets,
                "total_errors": total_errors,
                "total_duration_minutes": round(total_duration, 2),
                "error_rate": round(error_rate, 4),
                "productivity_score": round(productivity, 3),
                "average_complexity": round(avg_complexity, 3),
                "peak_hours": peak_hours,
                "dominant_pattern": dominant_pattern.value,
                "top_tools": sorted(all_tools.items(), key=lambda x: x[1], reverse=True)[:10],
                "insight_count": len(self._insights),
            }

    def get_stats(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        return self.get_developer_model(profile_id)

    # ------------------------------------------------------------------
    # Tool Suggestions
    # ------------------------------------------------------------------

    def suggest_tool_shortcuts(self, profile_id: Optional[str] = None) -> List[str]:
        with self._lock:
            footprints = self.list_footprints(profile_id)
            if not footprints:
                return self._default_tool_suggestions()

            tool_counts: Dict[str, int] = {}
            tool_recent: Dict[str, float] = {}

            for fp in footprints:
                for tool in fp.tools_used:
                    tool_counts[tool] = tool_counts.get(tool, 0) + 1
                    if fp.timestamp > tool_recent.get(tool, 0.0):
                        tool_recent[tool] = fp.timestamp

            now = _time_module.time()
            suggestions: List[Tuple[str, float]] = []

            for tool, count in tool_counts.items():
                recency = tool_recent.get(tool, 0.0)
                recency_score = max(0.0, 1.0 - (now - recency) / (7 * 86400))
                score = (count / max(len(footprints), 1)) * 0.6 + recency_score * 0.4
                suggestions.append((tool, score))

            suggestions.sort(key=lambda x: x[1], reverse=True)

            result: List[str] = []
            seen: set = set()

            for tool, _ in suggestions:
                if tool not in seen:
                    seen.add(tool)
                    result.append(tool)
                if len(result) >= 5:
                    break

            return result

    # ------------------------------------------------------------------
    # Action Prediction
    # ------------------------------------------------------------------

    def predict_next_action(self, current_context: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            recent_tool = current_context.get("last_tool", "")
            recent_error = current_context.get("last_error", False)
            session_duration = current_context.get("session_duration", 0.0)
            profile_id = current_context.get("profile_id")

            footprints = self.list_footprints(profile_id)
            transition_counts: Dict[str, Dict[str, int]] = {}

            sorted_fps = sorted(footprints, key=lambda f: f.timestamp)
            for i in range(len(sorted_fps) - 1):
                curr_tools = sorted_fps[i].tools_used
                next_tools = sorted_fps[i + 1].tools_used
                for ct in curr_tools:
                    if ct not in transition_counts:
                        transition_counts[ct] = {}
                    for nt in next_tools:
                        transition_counts[ct][nt] = transition_counts[ct].get(nt, 0) + 1

            predicted_tool = "code_generation"
            confidence = 0.3

            if recent_tool and recent_tool in transition_counts:
                transitions = transition_counts[recent_tool]
                if transitions:
                    total = sum(transitions.values())
                    best_tool = max(transitions, key=transitions.get)
                    confidence = transitions[best_tool] / total
                    predicted_tool = best_tool

            if recent_error:
                predicted_tool = "debugging"
                confidence = max(confidence, 0.65)

            if session_duration > 120:
                predicted_tool = "refactoring"
                confidence = max(confidence, 0.5)

            return {
                "predicted_tool": predicted_tool,
                "confidence": round(confidence, 3),
                "reasoning": self._explain_prediction(
                    predicted_tool, recent_tool, recent_error, session_duration
                ),
            }

    # ------------------------------------------------------------------
    # Learning Recommendations
    # ------------------------------------------------------------------

    def get_learning_recommendations(self, profile_id: Optional[str] = None) -> List[str]:
        with self._lock:
            footprints = self.list_footprints(profile_id)
            recommendations: List[str] = []

            if not footprints:
                return [
                    "Start with the SparkLabs Getting Started guide to set up your first project",
                    "Explore the visual scripting system for rapid prototyping",
                    "Review the asset pipeline documentation for importing game assets",
                ]

            error_rate_total = sum(fp.error_rate() for fp in footprints) / len(footprints)
            if error_rate_total > 0.15:
                recommendations.append(
                    "Your error rate is above 15%. Review the debugging workflow guide "
                    "and consider using the interactive debugger for complex issues."
                )

            tool_set = set()
            for fp in footprints:
                tool_set.update(fp.tools_used)

            essential_tools = {
                "code_generation", "debugging", "testing",
                "build_system", "game_design", "asset_management",
            }
            missing = essential_tools - tool_set
            for tool in sorted(missing):
                recommendations.append(
                    f"You have not used the {tool} tool yet. Explore it to improve "
                    f"your development workflow."
                )

            complexities = [fp.complexity_score for fp in footprints]
            if complexities:
                avg_complexity = sum(complexities) / len(complexities)
                if avg_complexity < 0.3:
                    recommendations.append(
                        "Your sessions show low complexity. Try tackling more "
                        "ambitious features like physics systems or procedural generation."
                    )
                elif avg_complexity > 0.8:
                    recommendations.append(
                        "Your sessions are highly complex. Consider breaking large "
                        "features into smaller, well-scoped modules for better maintainability."
                    )

            durations = [fp.duration_minutes for fp in footprints]
            if durations:
                avg_duration = sum(durations) / len(durations)
                if avg_duration > 180:
                    recommendations.append(
                        "Your sessions tend to run long (3+ hours). Consider taking "
                        "regular breaks and using checkpoints to save incremental progress."
                    )

            if profile_id and profile_id in self._profiles:
                profile = self._profiles[profile_id]
                if profile.expertise in (DevExpertise.NOVICE, DevExpertise.INTERMEDIATE):
                    recommendations.append(
                        "As you build skills, explore the Agent Studio to delegate "
                        "tasks to specialized AI agents for faster iteration."
                    )

            if len(recommendations) < 3:
                defaults = [
                    "Try the collaboration features to work with AI agents on larger projects",
                    "Experiment with different game genres to broaden your design skills",
                    "Use the performance profiler to identify optimization opportunities",
                ]
                for rec in defaults:
                    if len(recommendations) >= 5:
                        break
                    recommendations.append(rec)

            return recommendations[:5]

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _normalize_tool_name(self, tool_name: str) -> str:
        lowered = tool_name.lower().strip()
        return self._tool_aliases.get(lowered, lowered)

    def _compute_complexity(
        self,
        commands: int,
        snippets: int,
        errors: int,
        duration: float,
    ) -> float:
        if duration <= 0:
            return 0.0
        base = math.log1p(commands + snippets) / math.log1p(duration)
        error_penalty = 1.0 / (1.0 + math.log1p(errors))
        raw = base * error_penalty
        return round(min(max(raw, 0.0), 1.0), 4)

    def _index_footprint(self, profile_id: str, footprint_id: str) -> None:
        if profile_id not in self._footprint_index:
            self._footprint_index[profile_id] = []
        self._footprint_index[profile_id].append(footprint_id)

    def _update_profile_from_footprint(
        self, profile_id: str, footprint: SessionFootprint
    ) -> None:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return

        profile.session_count += 1
        profile.updated_at = _time_module.time()

        hour = _time_module.localtime(footprint.timestamp).tm_hour
        profile.active_hours.append(hour)

        for tool in footprint.tools_used:
            profile.tool_frequency[tool] = profile.tool_frequency.get(tool, 0) + 1

    def _record_interaction(
        self, session_id: str, footprint: SessionFootprint
    ) -> None:
        entry = {
            "session_id": session_id,
            "timestamp": footprint.timestamp,
            "tools_used": list(footprint.tools_used),
            "commands": footprint.commands_issued,
            "errors": footprint.errors_encountered,
            "duration": footprint.duration_minutes,
        }
        self._interaction_history.append(entry)
        if len(self._interaction_history) > self._max_history:
            self._interaction_history = self._interaction_history[-self._max_history:]

    def _compute_peak_hours(self, hours: List[int]) -> List[int]:
        if not hours:
            return [9, 10, 11, 14, 15, 16]
        counts: Dict[int, int] = {}
        for h in hours:
            counts[h] = counts.get(h, 0) + 1
        sorted_hours = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        peak = [h for h, _ in sorted_hours[:6]]
        return sorted(peak)

    def _compute_interaction_pattern(
        self, footprints: List[SessionFootprint]
    ) -> InteractionPattern:
        if not footprints:
            return InteractionPattern.BALANCED

        total_code = sum(fp.code_snippets_created for fp in footprints)
        total_design = 0
        design_keywords = {"game_design", "narrative", "level_design", "ui_design", "dialogue"}
        debug_keywords = {"debugging", "testing", "code_review"}

        for fp in footprints:
            for tool in fp.tools_used:
                if tool in design_keywords:
                    total_design += 1

        total_debug = 0
        for fp in footprints:
            for tool in fp.tools_used:
                if tool in debug_keywords:
                    total_debug += 1

        total_activity = total_code + total_design + total_debug
        if total_activity == 0:
            return InteractionPattern.EXPLORATORY

        code_ratio = total_code / total_activity
        design_ratio = total_design / total_activity
        debug_ratio = total_debug / total_activity

        if debug_ratio > 0.4:
            return InteractionPattern.DEBUGGING
        if code_ratio > 0.6:
            return InteractionPattern.CODE_HEAVY
        if design_ratio > 0.6:
            return InteractionPattern.DESIGN_HEAVY
        if code_ratio < 0.3 and design_ratio < 0.3:
            return InteractionPattern.EXPLORATORY
        return InteractionPattern.BALANCED

    def _derive_tool_insights(
        self, footprints: List[SessionFootprint]
    ) -> List[DevInsight]:
        insights: List[DevInsight] = []
        tool_counts: Dict[str, int] = {}
        for fp in footprints:
            for tool in fp.tools_used:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        if not tool_counts:
            return insights

        session_ids = [fp.session_id for fp in footprints]
        max_tool = max(tool_counts, key=tool_counts.get)
        max_count = tool_counts[max_tool]
        confidence = min(max_count / max(len(footprints), 1), 1.0)

        if confidence > 0.5:
            insights.append(
                DevInsight(
                    insight_type="tool_preference",
                    description=f"Developer heavily favors the '{max_tool}' tool, "
                    f"used in {max_count} of {len(footprints)} sessions.",
                    confidence=confidence,
                    derived_from_sessions=session_ids,
                )
            )

        unique_tools = len(tool_counts)
        if unique_tools <= 2 and len(footprints) >= 3:
            insights.append(
                DevInsight(
                    insight_type="narrow_tool_set",
                    description=f"Developer uses only {unique_tools} distinct tools "
                    f"across {len(footprints)} sessions. May benefit from broader tool exploration.",
                    confidence=0.75,
                    derived_from_sessions=session_ids,
                )
            )

        if unique_tools >= 8:
            insights.append(
                DevInsight(
                    insight_type="broad_tool_adoption",
                    description=f"Developer uses {unique_tools} distinct tools, "
                    f"indicating broad exploration of the tool ecosystem.",
                    confidence=0.7,
                    derived_from_sessions=session_ids,
                )
            )

        return insights

    def _derive_productivity_insights(
        self, footprints: List[SessionFootprint]
    ) -> List[DevInsight]:
        insights: List[DevInsight] = []
        if len(footprints) < 3:
            return insights

        session_ids = [fp.session_id for fp in footprints]
        scores = [fp.productivity_score() for fp in footprints]
        avg_score = sum(scores) / len(scores)

        recent = scores[-3:]
        recent_avg = sum(recent) / len(recent)

        if recent_avg > avg_score * 1.2:
            insights.append(
                DevInsight(
                    insight_type="productivity_growth",
                    description="Recent productivity is trending upward, "
                    f"with a 20%+ improvement over the historical average.",
                    confidence=0.65,
                    derived_from_sessions=session_ids[-3:],
                )
            )

        if recent_avg < avg_score * 0.8 and avg_score > 0.1:
            insights.append(
                DevInsight(
                    insight_type="productivity_decline",
                    description="Recent productivity has declined. Consider reviewing "
                    "workflow bottlenecks or tooling friction.",
                    confidence=0.6,
                    derived_from_sessions=session_ids[-3:],
                )
            )

        if all(s < 0.5 for s in scores) and len(scores) >= 4:
            insights.append(
                DevInsight(
                    insight_type="low_productivity",
                    description="Consistently low productivity scores across sessions. "
                    "Consider adopting more automated workflows and code generation tools.",
                    confidence=0.7,
                    derived_from_sessions=session_ids,
                )
            )

        return insights

    def _derive_error_insights(
        self, footprints: List[SessionFootprint]
    ) -> List[DevInsight]:
        insights: List[DevInsight] = []
        if not footprints:
            return insights

        session_ids = [fp.session_id for fp in footprints]
        error_rates = [fp.error_rate() for fp in footprints]
        avg_error = sum(error_rates) / len(error_rates)

        if avg_error > 0.2:
            insights.append(
                DevInsight(
                    insight_type="high_error_rate",
                    description=f"Average error rate of {avg_error:.1%} across sessions. "
                    "Consider incremental testing and code review workflows.",
                    confidence=min(avg_error * 3, 1.0),
                    derived_from_sessions=session_ids,
                )
            )

        if len(error_rates) >= 3:
            recent_errors = error_rates[-3:]
            if all(r < 0.05 for r in recent_errors) and avg_error > 0.1:
                insights.append(
                    DevInsight(
                        insight_type="error_rate_improvement",
                        description="Error rate has dropped significantly in recent sessions.",
                        confidence=0.7,
                        derived_from_sessions=session_ids[-3:],
                    )
                )

        high_error_fps = [fp for fp in footprints if fp.error_rate() > 0.3]
        if len(high_error_fps) >= 2:
            insights.append(
                DevInsight(
                    insight_type="frequent_error_spikes",
                    description=f"{len(high_error_fps)} sessions had error rates above 30%. "
                    "Investigate root causes in these high-error sessions.",
                    confidence=0.55,
                    derived_from_sessions=[fp.session_id for fp in high_error_fps],
                )
            )

        return insights

    def _derive_session_insights(
        self, footprints: List[SessionFootprint]
    ) -> List[DevInsight]:
        insights: List[DevInsight] = []
        if len(footprints) < 5:
            return insights

        session_ids = [fp.session_id for fp in footprints]
        durations = [fp.duration_minutes for fp in footprints]

        avg_duration = sum(durations) / len(durations)
        if avg_duration < 30:
            insights.append(
                DevInsight(
                    insight_type="short_sessions",
                    description=f"Average session duration is only {avg_duration:.0f} minutes. "
                    "Longer focused sessions may improve depth of work.",
                    confidence=0.6,
                    derived_from_sessions=session_ids,
                )
            )

        if avg_duration > 180:
            insights.append(
                DevInsight(
                    insight_type="marathon_sessions",
                    description=f"Average session duration is {avg_duration:.0f} minutes. "
                    "Consider breaking work into shorter, focused sessions.",
                    confidence=0.6,
                    derived_from_sessions=session_ids,
                )
            )

        timestamps = [fp.timestamp for fp in footprints if fp.timestamp > 0]
        if len(timestamps) >= 5:
            intervals = []
            sorted_ts = sorted(timestamps)
            for i in range(1, len(sorted_ts)):
                intervals.append(sorted_ts[i] - sorted_ts[i - 1])

            avg_interval = sum(intervals) / len(intervals)
            if avg_interval < 3600:
                insights.append(
                    DevInsight(
                        insight_type="high_frequency",
                        description="Sessions occur very frequently. Developer is highly engaged.",
                        confidence=0.7,
                        derived_from_sessions=session_ids,
                    )
                )
            elif avg_interval > 86400 * 3:
                insights.append(
                    DevInsight(
                        insight_type="infrequent_sessions",
                        description="Sessions are spaced days apart. Consider more regular "
                        "engagement for consistent progress.",
                        confidence=0.55,
                        derived_from_sessions=session_ids,
                    )
                )

        return insights

    def _derive_language_insights(
        self, footprints: List[SessionFootprint]
    ) -> List[DevInsight]:
        insights: List[DevInsight] = []
        session_ids = [fp.session_id for fp in footprints]

        snippet_total = sum(fp.code_snippets_created for fp in footprints)
        command_total = sum(fp.commands_issued for fp in footprints)

        if snippet_total == 0 and command_total > 0:
            return insights

        if snippet_total > 0:
            ratio = command_total / max(snippet_total, 1)
            if ratio > 5:
                insights.append(
                    DevInsight(
                        insight_type="command_oriented",
                        description="Developer issues many commands relative to code snippets. "
                        "May prefer CLI-driven workflows.",
                        confidence=0.5,
                        derived_from_sessions=session_ids,
                    )
                )
            elif ratio < 0.5 and snippet_total > 10:
                insights.append(
                    DevInsight(
                        insight_type="code_oriented",
                        description="Developer creates more code snippets than commands. "
                        "Heavy emphasis on hands-on coding.",
                        confidence=0.5,
                        derived_from_sessions=session_ids,
                    )
                )

        return insights

    def _explain_prediction(
        self,
        predicted_tool: str,
        recent_tool: str,
        recent_error: bool,
        session_duration: float,
    ) -> str:
        parts: List[str] = []

        if recent_error:
            parts.append("error was recently encountered")
        if recent_tool and predicted_tool != recent_tool:
            parts.append(f"pattern after '{recent_tool}' often leads to '{predicted_tool}'")
        if session_duration > 120:
            parts.append("long session suggests refactoring or optimization needs")

        if not parts:
            parts.append("based on overall session patterns")

        return "; ".join(parts)

    def _default_tool_suggestions(self) -> List[str]:
        return [
            "code_generation",
            "game_design",
            "build_system",
            "testing",
            "debugging",
        ]

    # ------------------------------------------------------------------
    # Context Tracking
    # ------------------------------------------------------------------

    def set_project_context(
        self,
        profile_id: str,
        phase: ProjectPhase = ProjectPhase.IDEATION,
        genre: str = "",
        engine: str = "",
        target_platform: str = "",
    ) -> None:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return
            if not hasattr(self, "_project_contexts"):
                self._project_contexts: Dict[str, Dict[str, Any]] = {}
            self._project_contexts[profile_id] = {
                "phase": phase.value,
                "genre": genre,
                "engine": engine,
                "target_platform": target_platform,
                "updated_at": _time_module.time(),
            }

    def get_project_context(self, profile_id: str) -> Optional[Dict[str, Any]]:
        if not hasattr(self, "_project_contexts"):
            return None
        return self._project_contexts.get(profile_id)

    def update_project_phase(
        self, profile_id: str, phase: ProjectPhase
    ) -> bool:
        with self._lock:
            if not hasattr(self, "_project_contexts"):
                self._project_contexts: Dict[str, Dict[str, Any]] = {}
            ctx = self._project_contexts.get(profile_id)
            if ctx is None:
                return False
            ctx["phase"] = phase.value
            ctx["updated_at"] = _time_module.time()
            return True

    # ------------------------------------------------------------------
    # Expertise Progression
    # ------------------------------------------------------------------

    def assess_expertise_progression(
        self, profile_id: str
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None

            footprints = self.list_footprints(profile_id)
            if len(footprints) < 5:
                return {
                    "current_level": profile.expertise.value,
                    "progression_possible": False,
                    "reason": f"Only {len(footprints)} sessions recorded. Need at least 5 for assessment.",
                    "sessions_needed": 5 - len(footprints),
                }

            avg_complexity = sum(fp.complexity_score for fp in footprints) / len(footprints)
            avg_productivity = sum(fp.productivity_score() for fp in footprints) / len(footprints)
            error_trend = self._compute_error_trend(footprints)

            level_order = [
                DevExpertise.NOVICE,
                DevExpertise.INTERMEDIATE,
                DevExpertise.ADVANCED,
                DevExpertise.EXPERT,
                DevExpertise.MASTER,
            ]
            current_index = level_order.index(profile.expertise)

            score = (avg_complexity * 0.35 + avg_productivity * 0.35 + error_trend * 0.3)

            progression_possible = False
            next_level = profile.expertise
            if score > 0.7 and current_index < len(level_order) - 1:
                progression_possible = True
                next_level = level_order[current_index + 1]

            return {
                "current_level": profile.expertise.value,
                "next_level": next_level.value,
                "progression_possible": progression_possible,
                "progression_score": round(score, 3),
                "complexity_contribution": round(avg_complexity * 0.35, 3),
                "productivity_contribution": round(avg_productivity * 0.35, 3),
                "error_trend_contribution": round(error_trend * 0.3, 3),
                "total_sessions_assessed": len(footprints),
            }

    def promote_expertise(self, profile_id: str) -> Optional[DevProfile]:
        with self._lock:
            assessment = self.assess_expertise_progression(profile_id)
            if assessment is None or not assessment.get("progression_possible"):
                return None

            profile = self._profiles.get(profile_id)
            if profile is None:
                return None

            level_order = [
                DevExpertise.NOVICE,
                DevExpertise.INTERMEDIATE,
                DevExpertise.ADVANCED,
                DevExpertise.EXPERT,
                DevExpertise.MASTER,
            ]
            current_index = level_order.index(profile.expertise)
            if current_index < len(level_order) - 1:
                profile.expertise = level_order[current_index + 1]
                profile.updated_at = _time_module.time()
            return profile

    def _compute_error_trend(self, footprints: List[SessionFootprint]) -> float:
        if len(footprints) < 3:
            return 0.5

        sorted_fps = sorted(footprints, key=lambda f: f.timestamp)
        half = len(sorted_fps) // 2
        older = sorted_fps[:half]
        newer = sorted_fps[half:]

        older_error = sum(fp.error_rate() for fp in older) / max(len(older), 1)
        newer_error = sum(fp.error_rate() for fp in newer) / max(len(newer), 1)

        if older_error == 0:
            return 0.5 + newer_error * 0.5

        improvement = (older_error - newer_error) / older_error
        return max(0.0, min(1.0, (improvement + 1.0) / 2.0))

    # ------------------------------------------------------------------
    # Session Summarization
    # ------------------------------------------------------------------

    def summarize_developer(
        self, profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        with self._lock:
            model = self.get_developer_model(profile_id)
            profiles = (
                [self._profiles[profile_id]]
                if profile_id and profile_id in self._profiles
                else list(self._profiles.values())
            )

            insights = self.get_insights(min_confidence=0.5)
            suggestions = self.suggest_tool_shortcuts(profile_id)
            recommendations = self.get_learning_recommendations(profile_id)

            profile_summaries = []
            for p in profiles:
                profile_summaries.append(
                    {
                        "name": p.name,
                        "role": p.role.value,
                        "expertise": p.expertise.value,
                        "language": p.preferred_language,
                        "sessions": p.session_count,
                        "top_tools": [t for t, _ in p.top_tools(5)],
                    }
                )

            return {
                "profiles": profile_summaries,
                "aggregate_stats": model,
                "insights": [ins.to_dict() for ins in insights],
                "tool_suggestions": suggestions,
                "learning_recommendations": recommendations,
                "generated_at": _time_module.time(),
            }

    # ------------------------------------------------------------------
    # Data Export
    # ------------------------------------------------------------------

    def export_all_data(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "profiles": [p.to_dict() for p in self._profiles.values()],
                "footprints": [f.to_dict() for f in self._footprints.values()],
                "insights": [i.to_dict() for i in self._insights.values()],
                "exported_at": _time_module.time(),
                "version": "1.0",
            }

    def import_data(self, data: Dict[str, Any]) -> int:
        with self._lock:
            count = 0
            for pdata in data.get("profiles", []):
                profile = DevProfile(
                    id=pdata.get("id", uuid.uuid4().hex),
                    name=pdata.get("name", ""),
                    role=DevRole(pdata.get("role", "solo_dev")),
                    expertise=DevExpertise(pdata.get("expertise", "novice")),
                    preferred_language=pdata.get("preferred_language", "python"),
                    tool_frequency=pdata.get("tool_frequency", {}),
                    session_count=pdata.get("session_count", 0),
                    active_hours=pdata.get("active_hours", []),
                    created_at=pdata.get("created_at", _time_module.time()),
                    updated_at=pdata.get("updated_at", _time_module.time()),
                )
                self._profiles[profile.id] = profile
                count += 1

            for fdata in data.get("footprints", []):
                footprint = SessionFootprint(
                    id=fdata.get("id", uuid.uuid4().hex),
                    session_id=fdata.get("session_id", ""),
                    tools_used=fdata.get("tools_used", []),
                    commands_issued=fdata.get("commands_issued", 0),
                    code_snippets_created=fdata.get("code_snippets_created", 0),
                    errors_encountered=fdata.get("errors_encountered", 0),
                    duration_minutes=fdata.get("duration_minutes", 0.0),
                    complexity_score=fdata.get("complexity_score", 0.0),
                    timestamp=fdata.get("timestamp", _time_module.time()),
                )
                self._footprints[footprint.id] = footprint
                count += 1

            for idata in data.get("insights", []):
                insight = DevInsight(
                    id=idata.get("id", uuid.uuid4().hex),
                    insight_type=idata.get("insight_type", ""),
                    description=idata.get("description", ""),
                    confidence=idata.get("confidence", 0.0),
                    derived_from_sessions=idata.get("derived_from_sessions", []),
                    created_at=idata.get("created_at", _time_module.time()),
                )
                self._insights[insight.id] = insight
                count += 1

            return count

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self, profile_id: Optional[str] = None) -> None:
        with self._lock:
            if profile_id is None:
                self._profiles.clear()
                self._footprints.clear()
                self._insights.clear()
                self._footprint_index.clear()
                self._interaction_history.clear()
                if hasattr(self, "_project_contexts"):
                    self._project_contexts.clear()
            else:
                self._profiles.pop(profile_id, None)
                self._footprint_index.pop(profile_id, None)
                to_remove_fp = [
                    fid
                    for fid, fp in self._footprints.items()
                    if fp.session_id.startswith(profile_id)
                ]
                for fid in to_remove_fp:
                    del self._footprints[fid]
                to_remove_ins = [
                    iid
                    for iid, ins in self._insights.items()
                    if profile_id in ins.derived_from_sessions
                ]
                for iid in to_remove_ins:
                    del self._insights[iid]
                if hasattr(self, "_project_contexts"):
                    self._project_contexts.pop(profile_id, None)


def get_developer_oracle() -> DeveloperOracle:
    return DeveloperOracle.get_instance()