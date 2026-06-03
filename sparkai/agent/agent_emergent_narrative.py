"""
SparkLabs Agent - Emergent Narrative Engine

Narrative generation engine that creates dynamic storylines from
autonomous agent interactions. Weaves individual agent actions,
social dynamics, and world events into coherent emergent narratives
without pre-scripted plots.

Architecture:
  AgentEmergentNarrative (Singleton)
    |-- Story Weaver (thread individual events into story arcs)
    |-- Arc Tracker (monitor active story arcs and their progress)
    |-- Conflict Generator (create dramatic tension from agent goals)
    |-- Theme Analyzer (identify emerging themes in the narrative)
    |-- Climax Detector (recognize narrative climax points)
    |-- Resolution Composer (generate satisfying story resolutions)
    |-- Narrative Memory (persist story history across sessions)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class StoryArcType(Enum):
    HERO_JOURNEY = "hero_journey"
    TRAGEDY = "tragedy"
    COMEDY = "comedy"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    REVENGE = "revenge"
    REDEMPTION = "redemption"
    DISCOVERY = "discovery"
    CONFLICT = "conflict"
    ALLIANCE = "alliance"


class ArcPhase(Enum):
    INCITING = "inciting"
    RISING = "rising"
    CRISIS = "crisis"
    CLIMAX = "climax"
    FALLING = "falling"
    RESOLUTION = "resolution"
    COMPLETE = "complete"


class EventSignificance(Enum):
    TRIVIAL = "trivial"
    MINOR = "minor"
    NOTABLE = "notable"
    MAJOR = "major"
    PIVOTAL = "pivotal"
    LEGENDARY = "legendary"


class NarrativeTheme(Enum):
    POWER = "power"
    LOVE = "love"
    BETRAYAL = "betrayal"
    SACRIFICE = "sacrifice"
    FREEDOM = "freedom"
    JUSTICE = "justice"
    IDENTITY = "identity"
    SURVIVAL = "survival"
    AMBITION = "ambition"
    LOYALTY = "loyalty"
    CORRUPTION = "corruption"
    HOPE = "hope"


@dataclass
class NarrativeEvent:
    """Atomic narrative event in the story."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    event_type: str = ""
    description: str = ""
    involved_agents: List[str] = field(default_factory=list)
    location: str = ""
    significance: EventSignificance = EventSignificance.MINOR
    related_arcs: List[str] = field(default_factory=list)
    themes: List[NarrativeTheme] = field(default_factory=list)
    emotional_weight: float = 0.0
    causality: Dict[str, str] = field(default_factory=dict)  # event_id -> relationship

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "description": self.description,
            "involved_agents": self.involved_agents,
            "location": self.location,
            "significance": self.significance.value,
            "related_arcs": self.related_arcs,
            "themes": [t.value for t in self.themes],
            "emotional_weight": self.emotional_weight,
            "causality": self.causality,
        }


@dataclass
class StoryArc:
    """Ongoing narrative arc tracking."""
    arc_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    arc_type: StoryArcType = StoryArcType.CONFLICT
    title: str = ""
    description: str = ""
    protagonist_id: str = ""
    antagonist_id: str = ""
    phase: ArcPhase = ArcPhase.INCITING
    events: List[str] = field(default_factory=list)  # event_ids
    themes: List[NarrativeTheme] = field(default_factory=list)
    tension_level: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    last_updated: float = field(default_factory=_time_module.time)
    resolution_quality: float = 0.0
    is_active: bool = True
    involved_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arc_id": self.arc_id,
            "arc_type": self.arc_type.value,
            "title": self.title,
            "description": self.description,
            "protagonist_id": self.protagonist_id,
            "antagonist_id": self.antagonist_id,
            "phase": self.phase.value,
            "event_count": len(self.events),
            "themes": [t.value for t in self.themes],
            "tension_level": self.tension_level,
            "created_at": self.created_at,
            "is_active": self.is_active,
            "resolution_quality": self.resolution_quality,
            "involved_agents": self.involved_agents,
        }


@dataclass
class NarrativeSummary:
    """Summary of the current narrative state."""
    summary_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    active_arcs: int = 0
    completed_arcs: int = 0
    total_events: int = 0
    dominant_themes: List[str] = field(default_factory=list)
    overall_tension: float = 0.0
    narrative_quality: float = 0.0
    world_state: str = ""
    key_players: List[str] = field(default_factory=list)
    recent_developments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "timestamp": self.timestamp,
            "active_arcs": self.active_arcs,
            "completed_arcs": self.completed_arcs,
            "total_events": self.total_events,
            "dominant_themes": self.dominant_themes,
            "overall_tension": self.overall_tension,
            "narrative_quality": self.narrative_quality,
            "world_state": self.world_state,
            "key_players": self.key_players,
            "recent_developments": self.recent_developments,
        }


class AgentEmergentNarrative:
    """
    Emergent narrative generation engine.

    Weaves autonomous agent actions into coherent storylines by
    tracking narrative arcs, identifying dramatic patterns, and
    generating meaningful story structures from emergent gameplay.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._events: Dict[str, NarrativeEvent] = {}
        self._arcs: Dict[str, StoryArc] = {}
        self._summaries: List[NarrativeSummary] = []
        self._total_events: int = 0
        self._narrative_context: str = ""

        # Arc type templates for auto-generation
        self._arc_templates: Dict[StoryArcType, Dict[str, Any]] = {
            StoryArcType.CONFLICT: {
                "phases": [ArcPhase.INCITING, ArcPhase.RISING, ArcPhase.CRISIS, ArcPhase.CLIMAX, ArcPhase.RESOLUTION],
                "themes": [NarrativeTheme.POWER, NarrativeTheme.BETRAYAL],
                "tension_curve": [0.1, 0.3, 0.6, 0.9, 0.2],
            },
            StoryArcType.ALLIANCE: {
                "phases": [ArcPhase.INCITING, ArcPhase.RISING, ArcPhase.CLIMAX, ArcPhase.RESOLUTION],
                "themes": [NarrativeTheme.LOYALTY, NarrativeTheme.HOPE],
                "tension_curve": [0.1, 0.3, 0.5, 0.1],
            },
            StoryArcType.HERO_JOURNEY: {
                "phases": [ArcPhase.INCITING, ArcPhase.RISING, ArcPhase.CRISIS, ArcPhase.CLIMAX, ArcPhase.FALLING, ArcPhase.RESOLUTION],
                "themes": [NarrativeTheme.SACRIFICE, NarrativeTheme.IDENTITY, NarrativeTheme.HOPE],
                "tension_curve": [0.1, 0.3, 0.6, 0.9, 0.4, 0.1],
            },
            StoryArcType.TRAGEDY: {
                "phases": [ArcPhase.INCITING, ArcPhase.RISING, ArcPhase.CLIMAX, ArcPhase.RESOLUTION],
                "themes": [NarrativeTheme.AMBITION, NarrativeTheme.CORRUPTION],
                "tension_curve": [0.1, 0.4, 0.9, 0.7],
            },
            StoryArcType.REDEMPTION: {
                "phases": [ArcPhase.INCITING, ArcPhase.CRISIS, ArcPhase.RISING, ArcPhase.CLIMAX, ArcPhase.RESOLUTION],
                "themes": [NarrativeTheme.SACRIFICE, NarrativeTheme.LOYALTY],
                "tension_curve": [0.2, 0.5, 0.3, 0.7, 0.1],
            },
        }

    @classmethod
    def get_instance(cls) -> "AgentEmergentNarrative":
        return cls()

    # ---- Event Recording ----

    def record_event(
        self,
        event_type: str,
        description: str,
        involved_agents: Optional[List[str]] = None,
        location: str = "",
        significance: EventSignificance = EventSignificance.MINOR,
        themes: Optional[List[NarrativeTheme]] = None,
        emotional_weight: float = 0.0,
        related_arcs: Optional[List[str]] = None,
        causality: Optional[Dict[str, str]] = None,
    ) -> NarrativeEvent:
        """Record a narrative event in the story."""
        with self._lock:
            event = NarrativeEvent(
                event_type=event_type,
                description=description,
                involved_agents=involved_agents or [],
                location=location,
                significance=significance,
                themes=themes or [],
                emotional_weight=emotional_weight,
                related_arcs=related_arcs or [],
                causality=causality or {},
            )
            self._events[event.event_id] = event
            self._total_events += 1

            # Update related arcs
            for arc_id in event.related_arcs:
                arc = self._arcs.get(arc_id)
                if arc:
                    arc.events.append(event.event_id)
                    arc.last_updated = _time_module.time()
                    arc.tension_level = self._compute_arc_tension(arc)

            # Trim event history
            if len(self._events) > 5000:
                old_ids = sorted(self._events.keys())[:2500]
                for eid in old_ids:
                    del self._events[eid]

            return event

    # ---- Story Arc Management ----

    def create_arc(
        self,
        arc_type: StoryArcType,
        title: str,
        description: str = "",
        protagonist_id: str = "",
        antagonist_id: str = "",
        themes: Optional[List[NarrativeTheme]] = None,
        involved_agents: Optional[List[str]] = None,
    ) -> StoryArc:
        """Create a new narrative arc."""
        with self._lock:
            # Use template defaults if available
            template = self._arc_templates.get(arc_type, {})
            default_themes = template.get("themes", [])

            arc = StoryArc(
                arc_type=arc_type,
                title=title,
                description=description,
                protagonist_id=protagonist_id,
                antagonist_id=antagonist_id,
                themes=themes or default_themes,
                involved_agents=involved_agents or [],
            )
            self._arcs[arc.arc_id] = arc
            return arc

    def advance_arc_phase(self, arc_id: str) -> Optional[StoryArc]:
        """Advance a story arc to its next phase."""
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None or not arc.is_active:
                return None

            template = self._arc_templates.get(arc.arc_type, {})
            phases = template.get("phases", [])
            tension_curve = template.get("tension_curve", [])

            if arc.phase in phases:
                idx = phases.index(arc.phase)
                if idx + 1 < len(phases):
                    arc.phase = phases[idx + 1]
                    if idx + 1 < len(tension_curve):
                        arc.tension_level = tension_curve[idx + 1]
                    arc.last_updated = _time_module.time()

                    if arc.phase == ArcPhase.RESOLUTION:
                        arc.is_active = False
                        arc.resolution_quality = self._evaluate_resolution(arc)

            return arc

    def _compute_arc_tension(self, arc: StoryArc) -> float:
        """Compute the current tension level of an arc."""
        if not arc.events:
            return 0.0

        pivotal_count = sum(
            1 for eid in arc.events
            if self._events.get(eid) and self._events[eid].significance in (
                EventSignificance.PIVOTAL, EventSignificance.LEGENDARY,
            )
        )
        major_count = sum(
            1 for eid in arc.events
            if self._events.get(eid) and self._events[eid].significance == EventSignificance.MAJOR
        )

        base = len(arc.events) * 0.02
        pivotal_bonus = pivotal_count * 0.15
        major_bonus = major_count * 0.08

        return min(1.0, base + pivotal_bonus + major_bonus)

    def _evaluate_resolution(self, arc: StoryArc) -> float:
        """Evaluate the quality of a story arc resolution."""
        if not arc.events:
            return 0.0

        event_count = len(arc.events)
        pivotal_count = sum(
            1 for eid in arc.events
            if self._events.get(eid) and self._events[eid].significance
            in (EventSignificance.PIVOTAL, EventSignificance.LEGENDARY)
        )
        total_emotional = sum(
            self._events[eid].emotional_weight for eid in arc.events
            if eid in self._events
        )

        quality = (
            min(1.0, event_count / 10) * 0.3
            + min(1.0, pivotal_count / 3) * 0.3
            + min(1.0, total_emotional / 5) * 0.4
        )
        return quality

    # ---- Theme Analysis ----

    def analyze_themes(self) -> Dict[str, float]:
        """Analyze emerging themes across all active arcs."""
        theme_counts: Dict[str, float] = {}
        total_weight = 0.0

        for arc in self._arcs.values():
            if not arc.is_active:
                continue
            weight = arc.tension_level + 0.1
            for theme in arc.themes:
                theme_counts[theme.value] = (
                    theme_counts.get(theme.value, 0.0) + weight
                )
                total_weight += weight

        if total_weight > 0:
            for key in theme_counts:
                theme_counts[key] /= total_weight

        return theme_counts

    # ---- Conflict Generation ----

    def detect_emerging_conflicts(self) -> List[Dict[str, Any]]:
        """Detect potential conflicts between agents based on goals and relationships."""
        conflicts: List[Dict[str, Any]] = []

        # Analyze arcs for conflicting protagonists
        for a_id, arc_a in self._arcs.items():
            for b_id, arc_b in self._arcs.items():
                if a_id >= b_id or not arc_a.is_active or not arc_b.is_active:
                    continue

                if arc_a.protagonist_id == arc_b.antagonist_id:
                    conflicts.append({
                        "type": "direct_conflict",
                        "arc_a_id": a_id,
                        "arc_b_id": b_id,
                        "agent_a": arc_a.protagonist_id,
                        "agent_b": arc_b.protagonist_id,
                        "tension": (arc_a.tension_level + arc_b.tension_level) / 2,
                    })

        return conflicts

    # ---- Summary Generation ----

    def generate_summary(self) -> NarrativeSummary:
        """Generate a comprehensive narrative summary."""
        with self._lock:
            active = [a for a in self._arcs.values() if a.is_active]
            completed = [a for a in self._arcs.values() if not a.is_active]

            themes = self.analyze_themes()
            dominant = sorted(
                themes.items(), key=lambda x: x[1], reverse=True,
            )[:3]

            key_players = list(set([
                a.protagonist_id for a in self._arcs.values() if a.protagonist_id
            ] + [
                a.antagonist_id for a in self._arcs.values() if a.antagonist_id
            ]))

            recent = sorted(
                self._events.values(),
                key=lambda e: e.timestamp, reverse=True,
            )[:5]

            summary = NarrativeSummary(
                active_arcs=len(active),
                completed_arcs=len(completed),
                total_events=self._total_events,
                dominant_themes=[t[0] for t in dominant],
                overall_tension=(
                    sum(a.tension_level for a in active) / len(active)
                    if active else 0.0
                ),
                narrative_quality=(
                    sum(a.resolution_quality for a in completed) / len(completed)
                    if completed else 0.0
                ),
                key_players=key_players[:10],
                recent_developments=[e.description for e in recent],
            )
            self._summaries.append(summary)
            return summary

    # ---- Query Methods ----

    def get_arc(self, arc_id: str) -> Optional[Dict[str, Any]]:
        arc = self._arcs.get(arc_id)
        return arc.to_dict() if arc else None

    def get_active_arcs(self) -> List[Dict[str, Any]]:
        return [
            a.to_dict() for a in self._arcs.values()
            if a.is_active
        ]

    def get_completed_arcs(self) -> List[Dict[str, Any]]:
        return [
            a.to_dict() for a in self._arcs.values()
            if not a.is_active
        ]

    def get_events(
        self,
        arc_id: str = "",
        significance: Optional[EventSignificance] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query narrative events with filtering."""
        with self._lock:
            results = list(self._events.values())
            if arc_id:
                results = [e for e in results if arc_id in e.related_arcs]
            if significance is not None:
                results = [e for e in results if e.significance == significance]
            results.sort(key=lambda e: e.timestamp, reverse=True)
            return [e.to_dict() for e in results[:limit]]

    def get_agent_arcs(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all arcs involving a specific agent."""
        return [
            a.to_dict() for a in self._arcs.values()
            if agent_id in a.involved_agents
            or agent_id == a.protagonist_id
            or agent_id == a.antagonist_id
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get narrative engine statistics."""
        with self._lock:
            active = sum(1 for a in self._arcs.values() if a.is_active)
            completed = sum(1 for a in self._arcs.values() if not a.is_active)
            return {
                "total_events": self._total_events,
                "active_arcs": active,
                "completed_arcs": completed,
                "total_arcs": len(self._arcs),
                "arc_types": {t.value: sum(1 for a in self._arcs.values() if a.arc_type == t) for t in StoryArcType},
                "dominant_themes": list(self.analyze_themes().keys()),
                "overall_tension": (
                    sum(a.tension_level for a in self._arcs.values() if a.is_active) / active
                    if active else 0.0
                ),
            }


# Module-level accessor
_emergent_narrative: Optional[AgentEmergentNarrative] = None


def get_emergent_narrative() -> AgentEmergentNarrative:
    global _emergent_narrative
    if _emergent_narrative is None:
        _emergent_narrative = AgentEmergentNarrative()
    return _emergent_narrative