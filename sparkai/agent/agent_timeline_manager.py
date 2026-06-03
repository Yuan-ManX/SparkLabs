"""
SparkLabs Agent - Timeline Manager

AI-driven timeline branching and narrative evolution system for the
SparkLabs AI-native game engine. Manages multiple parallel timelines,
branch points, event tracking, and timeline comparison/merging for
dynamic narrative generation.

Architecture:
  AgentTimelineManager (Singleton)
    |-- Timeline Creation & Branching (divergent narrative paths)
    |-- Event Recording (tracking in-world actions and consequences)
    |-- Timeline Advancement (progressive narrative evolution)
    |-- Timeline Merging (reconciling parallel branches)
    |-- Timeline Comparison (diffing divergent paths)
    |-- Alternate Generation (what-if scenario simulation)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TimelineStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FROZEN = "frozen"


class EventType(Enum):
    CHARACTER_ACTION = "character_action"
    WORLD_EVENT = "world_event"
    DISASTER = "disaster"
    DISCOVERY = "discovery"
    CONFLICT = "conflict"
    ALLIANCE = "alliance"
    REVELATION = "revelation"
    TRANSFORMATION = "transformation"


class BranchImportance(Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


EVENT_TYPE_IMPACT_WEIGHTS: Dict[EventType, float] = {
    EventType.CHARACTER_ACTION: 0.3,
    EventType.WORLD_EVENT: 0.5,
    EventType.DISASTER: 0.85,
    EventType.DISCOVERY: 0.45,
    EventType.CONFLICT: 0.7,
    EventType.ALLIANCE: 0.55,
    EventType.REVELATION: 0.65,
    EventType.TRANSFORMATION: 0.75,
}

BRANCH_IMPORTANCE_THRESHOLDS: Dict[BranchImportance, float] = {
    BranchImportance.MINOR: 0.2,
    BranchImportance.MODERATE: 0.45,
    BranchImportance.MAJOR: 0.7,
    BranchImportance.CRITICAL: 0.9,
}

TIMELINE_NARRATIVE_TEMPLATES: List[str] = [
    "The balance of power shifts as {agent_count} agents reshape the course of history.",
    "A {event_type} event reverberates across {region_count} regions, altering the world forever.",
    "In the wake of unprecedented change, {timeline_name} enters a new era of uncertainty.",
    "Ancient prophecies unfold as {event_count} pivotal events converge on a single moment.",
    "The threads of fate weave a new pattern, binding the destinies of {agent_count} souls.",
    "From the ashes of the old world, {timeline_name} rises with renewed purpose and vigor.",
    "A cascade of {branch_count} branching decisions creates a tapestry of intertwined destinies.",
    "The chronicles of {timeline_name} record a turning point that will be remembered for ages.",
]

EVENT_DESCRIPTION_TEMPLATES: Dict[EventType, List[str]] = {
    EventType.CHARACTER_ACTION: [
        "A decisive action taken by a key figure reshapes the political landscape.",
        "An unexpected hero emerges, performing a deed that alters the course of events.",
        "A betrayal from within shatters alliances and redraws the map of loyalties.",
        "A legendary feat of skill or courage inspires generations to come.",
    ],
    EventType.WORLD_EVENT: [
        "A celestial alignment triggers ancient mechanisms long dormant beneath the earth.",
        "The great convergence of trade routes transforms a remote outpost into a thriving hub.",
        "A cultural renaissance sweeps across the land, bringing art and innovation.",
        "Seasonal migrations shift, forcing entire populations to adapt or perish.",
    ],
    EventType.DISASTER: [
        "The earth trembles as a cataclysmic earthquake reshapes the terrain.",
        "A plague of mysterious origin spreads through crowded settlements with terrifying speed.",
        "Volcanic eruptions darken the skies, disrupting climate patterns for years to come.",
        "A great flood submerges coastal regions, displacing thousands and redrawing borders.",
    ],
    EventType.DISCOVERY: [
        "Explorers uncover a hidden valley teeming with flora never before catalogued.",
        "Ancient ruins reveal technology far beyond current understanding.",
        "A long-lost artifact is unearthed, its inscriptions speaking of forgotten empires.",
        "Scholars decipher a manuscript that rewrites the known history of the realm.",
    ],
    EventType.CONFLICT: [
        "Two rival factions clash over territorial claims, drawing allies into the fray.",
        "A border skirmish escalates into full-scale war, consuming resources and lives.",
        "An ideological schism divides a once-united kingdom into warring states.",
        "Mercenary armies converge on disputed lands, turning the region into a battlefield.",
    ],
    EventType.ALLIANCE: [
        "Former enemies forge an unprecedented pact, pooling resources for mutual survival.",
        "A marriage alliance between powerful houses seals peace after generations of feuding.",
        "Trade agreements open borders and create economic interdependence among nations.",
        "A council of elders forms a unified front against an encroaching external threat.",
    ],
    EventType.REVELATION: [
        "A hidden truth about the world's origins comes to light, shaking the foundations of belief.",
        "The true identity of a mysterious figure is revealed, rewriting political allegiances.",
        "Ancient prophecies are proven true as long-foretold signs manifest across the land.",
        "A secret society's machinations are exposed, revealing centuries of manipulation.",
    ],
    EventType.TRANSFORMATION: [
        "A region undergoes dramatic ecological change, its very nature transformed.",
        "A character transcends mortal limitations through arcane ritual or divine intervention.",
        "The metaphysical fabric of the world warps, altering the laws of reality itself.",
        "A civilization undergoes a paradigm shift, abandoning old ways for radical new systems.",
    ],
}

BRANCH_POINT_TEMPLATES: Dict[BranchImportance, List[str]] = {
    BranchImportance.MINOR: [
        "A minor character makes a seemingly insignificant choice.",
        "Two equally viable paths diverge at a crossroads of daily life.",
        "A small act of kindness or cruelty ripples outward.",
        "Local weather conditions affect a journey's outcome.",
    ],
    BranchImportance.MODERATE: [
        "A strategic decision with lasting tactical implications is made.",
        "An alliance is tested by competing interests and loyalties.",
        "Resources are allocated in a way that favors certain outcomes.",
        "A diplomatic overture is either accepted or rejected.",
    ],
    BranchImportance.MAJOR: [
        "A kingdom's fate hangs in the balance of a single battle.",
        "A leader must choose between two irreconcilable moral paths.",
        "The discovery of a powerful artifact demands a critical decision.",
        "A prophecy's interpretation leads down dramatically different roads.",
    ],
    BranchImportance.CRITICAL: [
        "The fundamental laws of the world can be rewritten or preserved.",
        "A god-like being offers a choice that will echo through eternity.",
        "Civilization itself stands at the precipice of salvation or annihilation.",
        "The timeline fractures at its root, creating irreconcilable realities.",
    ],
}

AGENT_NAME_POOL: List[str] = [
    "Aria_Shadowmere", "Kael_Firebrand", "Lyra_Stormwind", "Orin_Ironveil",
    "Sylas_Moonbrook", "Thalia_Dawnweaver", "Vex_Nightshade", "Zara_Sunforge",
    "Borin_Stonefist", "Elowen_Leafwhisper", "Fenris_Wolfbane", "Gideon_Lightward",
    "Helena_Frostborn", "Iskander_Sandstrider", "Juniper_Thornheart",
]

REGION_NAME_POOL: List[str] = [
    "Aetherwilds", "Blightmarch", "Crystalreach", "Dragonmoor",
    "Elderwood", "Frostveil", "Gloomfen", "Hallowvale",
    "Ironhold", "Jadewater", "Kingsfall", "Lunarshield",
    "Misthollow", "Noblecrest", "Opalwastes", "Pyrespine",
]


@dataclass
class TimelineEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeline_id: str = ""
    title: str = ""
    description: str = ""
    event_type: EventType = EventType.WORLD_EVENT
    impact_score: float = 0.0
    affected_agents: List[str] = field(default_factory=list)
    affected_regions: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timeline_id": self.timeline_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type.value,
            "impact_score": round(self.impact_score, 3),
            "affected_agents": self.affected_agents,
            "affected_regions": self.affected_regions,
            "prerequisites": self.prerequisites,
            "consequences": self.consequences,
            "timestamp": self.timestamp,
        }


@dataclass
class BranchPoint:
    branch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeline_id: str = ""
    description: str = ""
    conditions: List[str] = field(default_factory=list)
    possible_outcomes: List[str] = field(default_factory=list)
    chosen_outcome: str = ""
    branching_agents: List[str] = field(default_factory=list)
    importance: BranchImportance = BranchImportance.MODERATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "timeline_id": self.timeline_id,
            "description": self.description,
            "conditions": self.conditions,
            "possible_outcomes": self.possible_outcomes,
            "chosen_outcome": self.chosen_outcome,
            "branching_agents": self.branching_agents,
            "importance": self.importance.value,
        }


@dataclass
class TimelineBranch:
    timeline_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    name: str = ""
    description: str = ""
    root_timeline_id: str = ""
    branch_point_description: str = ""
    creation_event: str = ""
    events: List[str] = field(default_factory=list)
    status: TimelineStatus = TimelineStatus.ACTIVE
    created_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": self.timeline_id,
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "root_timeline_id": self.root_timeline_id,
            "branch_point_description": self.branch_point_description,
            "creation_event": self.creation_event,
            "event_count": len(self.events),
            "events": self.events,
            "status": self.status.value,
            "created_at": self.created_at,
        }


class AgentTimelineManager:
    """AI-driven timeline branching and narrative evolution system.

    Manages multiple parallel timelines within a game world, supporting
    branching narratives, event recording, timeline comparison, merging,
    and alternate timeline generation for dynamic storytelling.
    """

    _instance: Optional["AgentTimelineManager"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_EVENTS_PER_TIMELINE: int = 500
    MAX_BRANCHES_PER_TIMELINE: int = 50
    MAX_TIMELINES_PER_WORLD: int = 128
    MAX_BRANCH_DEPTH: int = 10
    DEFAULT_IMPACT_SCORE: float = 0.5

    def __new__(cls) -> "AgentTimelineManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentTimelineManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        _time_module.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._timelines: Dict[str, TimelineBranch] = {}
            self._events: Dict[str, TimelineEvent] = {}
            self._branch_points: Dict[str, BranchPoint] = {}
            self._timeline_order: Dict[str, List[str]] = {}
            self._world_timelines: Dict[str, List[str]] = {}
            self._branch_lineage: Dict[str, str] = {}
            self._total_timelines_created: int = 0
            self._total_events_recorded: int = 0
            self._total_branches_created: int = 0
            self._total_merges_performed: int = 0
            self._initialized = True

    def create_timeline(
        self,
        world_id: str,
        name: str = "Primary Timeline",
        description: str = "",
        root_timeline_id: str = "",
    ) -> TimelineBranch:
        _time_module.sleep(0.001)
        if world_id not in self._world_timelines:
            self._world_timelines[world_id] = []

        existing_count = len(self._world_timelines[world_id])
        if existing_count >= self.MAX_TIMELINES_PER_WORLD:
            raise ValueError(
                f"World {world_id} has reached maximum timeline count "
                f"({self.MAX_TIMELINES_PER_WORLD})"
            )

        if not description:
            rng = random.Random()
            description = rng.choice(TIMELINE_NARRATIVE_TEMPLATES).format(
                agent_count=rng.randint(3, 15),
                event_type=rng.choice(list(EventType)).value.replace("_", " "),
                region_count=rng.randint(2, 8),
                timeline_name=name,
                event_count=rng.randint(5, 50),
                branch_count=rng.randint(0, 10),
            )

        timeline = TimelineBranch(
            timeline_id=uuid.uuid4().hex,
            world_id=world_id,
            name=name,
            description=description,
            root_timeline_id=root_timeline_id or "",
            branch_point_description="",
            creation_event="",
            events=[],
            status=TimelineStatus.ACTIVE,
            created_at=_time_module.time(),
        )

        self._timelines[timeline.timeline_id] = timeline
        self._timeline_order[timeline.timeline_id] = []
        self._world_timelines[world_id].append(timeline.timeline_id)

        if not root_timeline_id:
            timeline.root_timeline_id = timeline.timeline_id

        self._total_timelines_created += 1
        return timeline

    def branch_timeline(
        self,
        parent_timeline_id: str,
        branch_name: str = "",
        branch_description: str = "",
        conditions: Optional[List[str]] = None,
        possible_outcomes: Optional[List[str]] = None,
        chosen_outcome: str = "",
        branching_agents: Optional[List[str]] = None,
        importance: BranchImportance = BranchImportance.MODERATE,
    ) -> TimelineBranch:
        _time_module.sleep(0.001)
        parent = self._timelines.get(parent_timeline_id)
        if parent is None:
            raise ValueError(f"Parent timeline {parent_timeline_id} not found")

        if parent.status in (TimelineStatus.ABANDONED, TimelineStatus.FROZEN):
            raise ValueError(
                f"Cannot branch from {parent.status.value} timeline {parent_timeline_id}"
            )

        rng = random.Random()
        branch_conditions = conditions or []
        branch_outcomes = possible_outcomes or []
        branch_agents = branching_agents or []

        if not branch_description:
            importance_templates = BRANCH_POINT_TEMPLATES.get(
                importance, BRANCH_POINT_TEMPLATES[BranchImportance.MODERATE]
            )
            branch_description = rng.choice(importance_templates)

        if not branch_name:
            existing_names = {
                t.name
                for t in self._timelines.values()
                if t.world_id == parent.world_id
            }
            suffixes = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
            for suffix in suffixes:
                candidate = f"{parent.name} - {suffix}"
                if candidate not in existing_names:
                    branch_name = candidate
                    break
            if not branch_name:
                branch_name = f"{parent.name} - Branch {len(parent.events) + 1}"

        if not branch_conditions:
            branch_conditions = [
                f"Agent {rng.choice(AGENT_NAME_POOL)} triggers divergence",
                f"Event in region {rng.choice(REGION_NAME_POOL)} alters course",
                f"Decision point reached at impact threshold {rng.uniform(0.3, 0.9):.2f}",
            ]

        if not branch_outcomes:
            branch_outcomes = [
                "Path of Light: prosperity and alliance flourish",
                "Path of Shadow: conflict and secrecy dominate",
                "Path of Balance: a middle way emerges",
            ]

        if not chosen_outcome and branch_outcomes:
            chosen_outcome = rng.choice(branch_outcomes)

        if not branch_agents:
            branch_agents = rng.sample(
                AGENT_NAME_POOL, rng.randint(1, min(4, len(AGENT_NAME_POOL)))
            )

        branch_point = BranchPoint(
            branch_id=uuid.uuid4().hex,
            timeline_id=parent_timeline_id,
            description=branch_description,
            conditions=branch_conditions,
            possible_outcomes=branch_outcomes,
            chosen_outcome=chosen_outcome,
            branching_agents=branch_agents,
            importance=importance,
        )
        self._branch_points[branch_point.branch_id] = branch_point

        timeline = TimelineBranch(
            timeline_id=uuid.uuid4().hex,
            world_id=parent.world_id,
            name=branch_name,
            description=parent.description,
            root_timeline_id=parent.root_timeline_id or parent.timeline_id,
            branch_point_description=branch_description,
            creation_event=branch_point.branch_id,
            events=list(parent.events),
            status=TimelineStatus.ACTIVE,
            created_at=_time_module.time(),
        )

        self._timelines[timeline.timeline_id] = timeline
        self._timeline_order[timeline.timeline_id] = list(
            self._timeline_order.get(parent_timeline_id, [])
        )
        self._world_timelines[parent.world_id].append(timeline.timeline_id)
        self._branch_lineage[timeline.timeline_id] = parent_timeline_id

        self._total_branches_created += 1
        self._total_timelines_created += 1
        return timeline

    def record_event(
        self,
        timeline_id: str,
        title: str,
        description: str,
        event_type: EventType = EventType.WORLD_EVENT,
        affected_agents: Optional[List[str]] = None,
        affected_regions: Optional[List[str]] = None,
        prerequisites: Optional[List[str]] = None,
        consequences: Optional[List[str]] = None,
        impact_score: Optional[float] = None,
    ) -> TimelineEvent:
        _time_module.sleep(0.001)
        timeline = self._timelines.get(timeline_id)
        if timeline is None:
            raise ValueError(f"Timeline {timeline_id} not found")

        if timeline.status != TimelineStatus.ACTIVE:
            raise ValueError(
                f"Cannot record event on {timeline.status.value} timeline {timeline_id}"
            )

        if len(timeline.events) >= self.MAX_EVENTS_PER_TIMELINE:
            raise ValueError(
                f"Timeline {timeline_id} has reached maximum event count "
                f"({self.MAX_EVENTS_PER_TIMELINE})"
            )

        event_agents = affected_agents or []
        event_regions = affected_regions or []
        event_prereqs = prerequisites or []
        event_consequences = consequences or []

        if impact_score is None:
            weight = EVENT_TYPE_IMPACT_WEIGHTS.get(
                event_type, self.DEFAULT_IMPACT_SCORE
            )
            rng = random.Random()
            impact_score = round(weight * rng.uniform(0.5, 1.5), 3)
            impact_score = max(0.0, min(1.0, impact_score))

        if not description:
            rng = random.Random()
            templates = EVENT_DESCRIPTION_TEMPLATES.get(
                event_type, EVENT_DESCRIPTION_TEMPLATES[EventType.WORLD_EVENT]
            )
            description = rng.choice(templates)

        if not event_regions:
            rng = random.Random()
            event_regions = rng.sample(
                REGION_NAME_POOL, rng.randint(1, min(3, len(REGION_NAME_POOL)))
            )

        if not event_agents:
            rng = random.Random()
            event_agents = rng.sample(
                AGENT_NAME_POOL, rng.randint(1, min(3, len(AGENT_NAME_POOL)))
            )

        event = TimelineEvent(
            event_id=uuid.uuid4().hex,
            timeline_id=timeline_id,
            title=title,
            description=description,
            event_type=event_type,
            impact_score=impact_score,
            affected_agents=event_agents,
            affected_regions=event_regions,
            prerequisites=event_prereqs,
            consequences=event_consequences,
            timestamp=_time_module.time(),
        )

        self._events[event.event_id] = event
        timeline.events.append(event.event_id)
        self._timeline_order[timeline_id].append(event.event_id)
        self._total_events_recorded += 1
        return event

    def advance_timeline(
        self,
        timeline_id: str,
        num_events: int = 1,
        event_type_filter: Optional[List[EventType]] = None,
    ) -> List[TimelineEvent]:
        _time_module.sleep(0.001)
        timeline = self._timelines.get(timeline_id)
        if timeline is None:
            raise ValueError(f"Timeline {timeline_id} not found")

        if timeline.status != TimelineStatus.ACTIVE:
            raise ValueError(
                f"Cannot advance {timeline.status.value} timeline {timeline_id}"
            )

        rng = random.Random()
        generated_events: List[TimelineEvent] = []

        types_pool = event_type_filter if event_type_filter else list(EventType)
        if not types_pool:
            types_pool = list(EventType)

        for _ in range(num_events):
            event_type = rng.choice(types_pool)
            weight = EVENT_TYPE_IMPACT_WEIGHTS.get(
                event_type, self.DEFAULT_IMPACT_SCORE
            )
            impact = round(weight * rng.uniform(0.5, 1.5), 3)
            impact = max(0.0, min(1.0, impact))

            title_prefixes: Dict[EventType, str] = {
                EventType.CHARACTER_ACTION: "The Deed of",
                EventType.WORLD_EVENT: "The Convergence at",
                EventType.DISASTER: "The Cataclysm of",
                EventType.DISCOVERY: "The Uncovering of",
                EventType.CONFLICT: "The Battle for",
                EventType.ALLIANCE: "The Pact of",
                EventType.REVELATION: "The Truth of",
                EventType.TRANSFORMATION: "The Metamorphosis of",
            }
            prefix = title_prefixes.get(event_type, "The Event at")
            location = rng.choice(REGION_NAME_POOL)
            title = f"{prefix} {location}"

            templates = EVENT_DESCRIPTION_TEMPLATES.get(
                event_type, EVENT_DESCRIPTION_TEMPLATES[EventType.WORLD_EVENT]
            )
            description = rng.choice(templates)

            event_agents = rng.sample(
                AGENT_NAME_POOL, rng.randint(1, min(3, len(AGENT_NAME_POOL)))
            )
            event_regions = rng.sample(
                REGION_NAME_POOL, rng.randint(1, min(3, len(REGION_NAME_POOL)))
            )

            prereqs: List[str] = []
            if len(timeline.events) >= 3:
                recent_events = rng.sample(
                    timeline.events, min(3, len(timeline.events))
                )
                prereqs = [eid for eid in recent_events if rng.random() < 0.5]

            consequences: List[str] = [
                f"Shift in regional power balance at {rng.choice(REGION_NAME_POOL)}",
                f"Realignment of agent loyalties among {rng.choice(AGENT_NAME_POOL)}'s faction",
                f"Discovery of new resource veins in affected territories",
            ]

            event = TimelineEvent(
                event_id=uuid.uuid4().hex,
                timeline_id=timeline_id,
                title=title,
                description=description,
                event_type=event_type,
                impact_score=impact,
                affected_agents=event_agents,
                affected_regions=event_regions,
                prerequisites=prereqs,
                consequences=consequences,
                timestamp=_time_module.time(),
            )

            self._events[event.event_id] = event
            timeline.events.append(event.event_id)
            self._timeline_order[timeline_id].append(event.event_id)
            self._total_events_recorded += 1
            generated_events.append(event)

        if generated_events:
            avg_impact = sum(e.impact_score for e in generated_events) / len(
                generated_events
            )
            if avg_impact > 0.85 and len(timeline.events) > 10:
                timeline.status = TimelineStatus.COMPLETED

        return generated_events

    def merge_timeline(
        self,
        primary_timeline_id: str,
        secondary_timeline_id: str,
        merge_strategy: str = "interleave",
    ) -> TimelineBranch:
        _time_module.sleep(0.001)
        primary = self._timelines.get(primary_timeline_id)
        if primary is None:
            raise ValueError(f"Primary timeline {primary_timeline_id} not found")

        secondary = self._timelines.get(secondary_timeline_id)
        if secondary is None:
            raise ValueError(f"Secondary timeline {secondary_timeline_id} not found")

        if primary.world_id != secondary.world_id:
            raise ValueError(
                f"Cannot merge timelines from different worlds: "
                f"{primary.world_id} vs {secondary.world_id}"
            )

        if primary.status == TimelineStatus.FROZEN or secondary.status == TimelineStatus.FROZEN:
            raise ValueError("Cannot merge frozen timelines")

        primary_events = list(self._timeline_order.get(primary_timeline_id, []))
        secondary_events = list(self._timeline_order.get(secondary_timeline_id, []))

        primary_event_set = set(primary_events)

        if merge_strategy == "interleave":
            merged_order: List[str] = []
            max_len = max(len(primary_events), len(secondary_events))
            rng = random.Random()
            for i in range(max_len):
                if i < len(primary_events):
                    merged_order.append(primary_events[i])
                if i < len(secondary_events):
                    se = secondary_events[i]
                    if se not in primary_event_set:
                        merged_order.append(se)
            merged_events = merged_order
        elif merge_strategy == "primary_first":
            merged_events = list(primary_events)
            for se in secondary_events:
                if se not in primary_event_set:
                    merged_events.append(se)
        elif merge_strategy == "unique_union":
            merged_set: Set[str] = set(primary_events)
            for se in secondary_events:
                merged_set.add(se)
            merged_events = sorted(
                merged_set,
                key=lambda eid: self._events[eid].timestamp
                if eid in self._events
                else 0.0,
            )
        else:
            merged_events = list(primary_events)

        merged_name = f"Merged: {primary.name} + {secondary.name}"
        rng = random.Random()
        merged_description = (
            f"Timeline formed from the convergence of '{primary.name}' and "
            f"'{secondary.name}', combining {len(merged_events)} events into "
            f"a unified narrative. Divergent paths reconciled at impact threshold "
            f"{rng.uniform(0.4, 0.8):.2f}."
        )

        merged = TimelineBranch(
            timeline_id=uuid.uuid4().hex,
            world_id=primary.world_id,
            name=merged_name,
            description=merged_description,
            root_timeline_id=primary.root_timeline_id,
            branch_point_description=(
                f"Merge of {primary_timeline_id} and {secondary_timeline_id}"
            ),
            creation_event="",
            events=merged_events,
            status=TimelineStatus.ACTIVE,
            created_at=_time_module.time(),
        )

        self._timelines[merged.timeline_id] = merged
        self._timeline_order[merged.timeline_id] = merged_events
        self._world_timelines[primary.world_id].append(merged.timeline_id)
        self._branch_lineage[merged.timeline_id] = primary_timeline_id

        secondary.status = TimelineStatus.COMPLETED
        self._total_merges_performed += 1
        self._total_timelines_created += 1
        return merged

    def compare_timelines(
        self, timeline_id_a: str, timeline_id_b: str
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        timeline_a = self._timelines.get(timeline_id_a)
        timeline_b = self._timelines.get(timeline_id_b)

        if timeline_a is None:
            raise ValueError(f"Timeline A {timeline_id_a} not found")
        if timeline_b is None:
            raise ValueError(f"Timeline B {timeline_id_b} not found")

        events_a = {
            eid: self._events[eid]
            for eid in self._timeline_order.get(timeline_id_a, [])
            if eid in self._events
        }
        events_b = {
            eid: self._events[eid]
            for eid in self._timeline_order.get(timeline_id_b, [])
            if eid in self._events
        }

        shared_ids = set(events_a.keys()) & set(events_b.keys())
        only_a_ids = set(events_a.keys()) - set(events_b.keys())
        only_b_ids = set(events_b.keys()) - set(events_a.keys())

        shared_events: List[Dict[str, Any]] = [
            self._events[eid].to_dict() for eid in sorted(shared_ids)
        ]
        divergent_events_a: List[Dict[str, Any]] = [
            self._events[eid].to_dict() for eid in sorted(only_a_ids)
        ]
        divergent_events_b: List[Dict[str, Any]] = [
            self._events[eid].to_dict() for eid in sorted(only_b_ids)
        ]

        type_counts_a: Dict[str, int] = {}
        type_counts_b: Dict[str, int] = {}
        for ev in events_a.values():
            t = ev.event_type.value
            type_counts_a[t] = type_counts_a.get(t, 0) + 1
        for ev in events_b.values():
            t = ev.event_type.value
            type_counts_b[t] = type_counts_b.get(t, 0) + 1

        avg_impact_a = 0.0
        avg_impact_b = 0.0
        if events_a:
            avg_impact_a = round(
                sum(e.impact_score for e in events_a.values()) / len(events_a), 3
            )
        if events_b:
            avg_impact_b = round(
                sum(e.impact_score for e in events_b.values()) / len(events_b), 3
            )

        overlap_ratio = 0.0
        total_unique = len(set(events_a.keys()) | set(events_b.keys()))
        if total_unique > 0:
            overlap_ratio = round(len(shared_ids) / total_unique, 3)

        divergence_score = 1.0 - overlap_ratio

        timeline_a_status = timeline_a.status.value
        timeline_b_status = timeline_b.status.value

        shared_root = (
            timeline_a.root_timeline_id == timeline_b.root_timeline_id
            and timeline_a.root_timeline_id
        )

        return {
            "timeline_a": {
                "id": timeline_id_a,
                "name": timeline_a.name,
                "status": timeline_a_status,
                "event_count": len(events_a),
                "average_impact": avg_impact_a,
                "event_type_distribution": type_counts_a,
            },
            "timeline_b": {
                "id": timeline_id_b,
                "name": timeline_b.name,
                "status": timeline_b_status,
                "event_count": len(events_b),
                "average_impact": avg_impact_b,
                "event_type_distribution": type_counts_b,
            },
            "shared_root_timeline_id": shared_root,
            "shared_events": shared_events,
            "shared_event_count": len(shared_ids),
            "divergent_events_a": divergent_events_a,
            "divergent_events_b": divergent_events_b,
            "divergent_count_a": len(only_a_ids),
            "divergent_count_b": len(only_b_ids),
            "overlap_ratio": overlap_ratio,
            "divergence_score": round(divergence_score, 3),
        }

    def get_timeline_history(
        self,
        timeline_id: str,
        include_events: bool = True,
        include_branches: bool = False,
        max_events: int = 100,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        timeline = self._timelines.get(timeline_id)
        if timeline is None:
            raise ValueError(f"Timeline {timeline_id} not found")

        ordered_event_ids = self._timeline_order.get(timeline_id, [])
        event_dicts: List[Dict[str, Any]] = []

        if include_events:
            event_ids_to_display = ordered_event_ids[:max_events]
            event_dicts = [
                self._events[eid].to_dict()
                for eid in event_ids_to_display
                if eid in self._events
            ]

        result: Dict[str, Any] = {
            "timeline": timeline.to_dict(),
            "total_events": len(timeline.events),
            "displayed_events": len(event_dicts),
            "events": event_dicts,
        }

        if include_branches:
            branches: List[Dict[str, Any]] = []
            for bid, bp in self._branch_points.items():
                if bp.timeline_id == timeline_id:
                    branches.append(bp.to_dict())
            result["branch_points"] = branches
            result["branch_count"] = len(branches)

        child_timelines: List[Dict[str, Any]] = []
        for tid, t in self._timelines.items():
            if self._branch_lineage.get(tid) == timeline_id:
                child_timelines.append(
                    {
                        "timeline_id": t.timeline_id,
                        "name": t.name,
                        "status": t.status.value,
                        "event_count": len(t.events),
                    }
                )
        result["child_timelines"] = child_timelines
        result["child_timeline_count"] = len(child_timelines)

        return result

    def generate_alternate_timeline(
        self,
        source_timeline_id: str,
        variation_prompt: str = "",
        num_variations: int = 1,
        divergence_impact: float = 0.5,
    ) -> List[TimelineBranch]:
        _time_module.sleep(0.001)
        source = self._timelines.get(source_timeline_id)
        if source is None:
            raise ValueError(f"Source timeline {source_timeline_id} not found")

        if source.status == TimelineStatus.FROZEN:
            raise ValueError(f"Cannot generate alternates from frozen timeline {source_timeline_id}")

        rng = random.Random()
        alternates: List[TimelineBranch] = []
        source_events = self._timeline_order.get(source_timeline_id, [])

        for var_idx in range(num_variations):
            if not variation_prompt:
                variation_prompt = rng.choice(
                    [
                        "What if the key alliance had never formed?",
                        "What if the great disaster had been prevented?",
                        "What if the discovery was made a century earlier?",
                        "What if the hero had chosen the other path?",
                        "What if the ancient artifact was never unearthed?",
                    ]
                )

            future_event_count = rng.randint(3, 15)
            future_events: List[str] = []

            for _ in range(future_event_count):
                event_type = rng.choice(list(EventType))
                impact = divergence_impact * rng.uniform(0.6, 1.4)
                impact = max(0.0, min(1.0, impact))

                event = TimelineEvent(
                    event_id=uuid.uuid4().hex,
                    timeline_id="",
                    title=f"Alternate: {event_type.value.replace('_', ' ').title()} in {rng.choice(REGION_NAME_POOL)}",
                    description=rng.choice(
                        EVENT_DESCRIPTION_TEMPLATES.get(
                            event_type,
                            EVENT_DESCRIPTION_TEMPLATES[EventType.WORLD_EVENT],
                        )
                    ),
                    event_type=event_type,
                    impact_score=round(impact, 3),
                    affected_agents=rng.sample(
                        AGENT_NAME_POOL, rng.randint(1, min(3, len(AGENT_NAME_POOL)))
                    ),
                    affected_regions=rng.sample(
                        REGION_NAME_POOL, rng.randint(1, min(3, len(REGION_NAME_POOL)))
                    ),
                    prerequisites=[],
                    consequences=[
                        f"Alternate outcome: {rng.choice(REGION_NAME_POOL)} diverges significantly",
                        f"Faction alignment shifts for {rng.choice(AGENT_NAME_POOL)}",
                    ],
                    timestamp=_time_module.time(),
                )
                self._events[event.event_id] = event
                future_events.append(event.event_id)
                self._total_events_recorded += 1

            combined_events = list(source_events) + future_events

            alt_suffixes = [
                "Mirror",
                "Reflection",
                "Echo",
                "Shadow",
                "Phantom",
                "Specter",
                "Vision",
                "Mirage",
            ]
            suffix = alt_suffixes[var_idx % len(alt_suffixes)]
            alt_name = f"{source.name} - {suffix}"

            alt_description = (
                f"Alternate timeline diverging from '{source.name}': "
                f"{variation_prompt}. "
                f"Impact threshold: {divergence_impact:.2f}. "
                f"Generated {future_event_count} divergent events."
            )

            alternate = TimelineBranch(
                timeline_id=uuid.uuid4().hex,
                world_id=source.world_id,
                name=alt_name,
                description=alt_description,
                root_timeline_id=source.root_timeline_id or source.timeline_id,
                branch_point_description=f"Alternate divergence: {variation_prompt}",
                creation_event="",
                events=combined_events,
                status=TimelineStatus.ACTIVE,
                created_at=_time_module.time(),
            )

            for eid in future_events:
                if eid in self._events:
                    self._events[eid].timeline_id = alternate.timeline_id

            self._timelines[alternate.timeline_id] = alternate
            self._timeline_order[alternate.timeline_id] = combined_events
            self._world_timelines[source.world_id].append(alternate.timeline_id)
            self._branch_lineage[alternate.timeline_id] = source_timeline_id
            self._total_timelines_created += 1

            alternates.append(alternate)

        return alternates

    def freeze_timeline(
        self,
        timeline_id: str,
        reason: str = "",
    ) -> TimelineBranch:
        _time_module.sleep(0.001)
        timeline = self._timelines.get(timeline_id)
        if timeline is None:
            raise ValueError(f"Timeline {timeline_id} not found")

        if timeline.status == TimelineStatus.FROZEN:
            return timeline

        previous_status = timeline.status.value
        timeline.status = TimelineStatus.FROZEN

        rng = random.Random()
        freeze_reason = reason or (
            f"Timeline '{timeline.name}' frozen to preserve narrative integrity "
            f"at event count {len(timeline.events)}. "
            f"Previous status: {previous_status}."
        )

        event = TimelineEvent(
            event_id=uuid.uuid4().hex,
            timeline_id=timeline_id,
            title=f"Timeline Frozen: {timeline.name}",
            description=freeze_reason,
            event_type=EventType.TRANSFORMATION,
            impact_score=1.0,
            affected_agents=[],
            affected_regions=[],
            prerequisites=[],
            consequences=[
                f"Timeline {timeline_id} is now preserved in its current state",
                "No further events can be recorded on this timeline",
                "Child timelines remain unaffected",
            ],
            timestamp=_time_module.time(),
        )

        self._events[event.event_id] = event
        timeline.events.append(event.event_id)
        self._timeline_order[timeline_id].append(event.event_id)
        self._total_events_recorded += 1

        return timeline

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        total_timelines = len(self._timelines)
        total_events = len(self._events)
        total_branches = len(self._branch_points)

        status_counts: Dict[str, int] = {}
        for t in self._timelines.values():
            s = t.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        world_timeline_counts: Dict[str, int] = {}
        for wid, tids in self._world_timelines.items():
            world_timeline_counts[wid] = len(tids)

        avg_events_per_timeline = 0.0
        if total_timelines > 0:
            avg_events_per_timeline = round(total_events / total_timelines, 2)

        max_event_timeline_id = ""
        max_event_count = 0
        for tid, t in self._timelines.items():
            if len(t.events) > max_event_count:
                max_event_count = len(t.events)
                max_event_timeline_id = tid

        branch_depths: Dict[str, int] = {}
        for tid in self._timelines:
            depth = 0
            current = tid
            while current in self._branch_lineage:
                depth += 1
                current = self._branch_lineage[current]
                if depth > self.MAX_BRANCH_DEPTH:
                    break
            branch_depths[tid] = depth

        avg_branch_depth = 0.0
        if branch_depths:
            avg_branch_depth = round(
                sum(branch_depths.values()) / len(branch_depths), 2
            )

        return {
            "total_timelines": total_timelines,
            "total_events": total_events,
            "total_branch_points": total_branches,
            "total_merges": self._total_merges_performed,
            "timelines_created_lifetime": self._total_timelines_created,
            "events_recorded_lifetime": self._total_events_recorded,
            "branches_created_lifetime": self._total_branches_created,
            "status_distribution": status_counts,
            "world_timeline_counts": world_timeline_counts,
            "average_events_per_timeline": avg_events_per_timeline,
            "max_event_timeline_id": max_event_timeline_id,
            "max_event_count": max_event_count,
            "average_branch_depth": avg_branch_depth,
            "max_branch_depth_limit": self.MAX_BRANCH_DEPTH,
            "max_events_per_timeline_limit": self.MAX_EVENTS_PER_TIMELINE,
            "max_timelines_per_world_limit": self.MAX_TIMELINES_PER_WORLD,
        }

    def list_timelines(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._timelines.values()]

    def list_events(self, timeline_id: str = "") -> List[Dict[str, Any]]:
        if timeline_id:
            ordered_ids = self._timeline_order.get(timeline_id, [])
            return [self._events[eid].to_dict() for eid in ordered_ids if eid in self._events]
        return [e.to_dict() for e in self._events.values()]


def get_timeline_manager() -> AgentTimelineManager:
    return AgentTimelineManager.get_instance()