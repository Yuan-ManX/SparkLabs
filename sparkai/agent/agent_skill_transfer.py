"""
SparkLabs Agent - Cross-Domain Skill Transfer Engine

Cross-domain skill transfer system for AI agents operating inside the
SparkLabs game engine. Agents migrate learned procedural knowledge from
one game domain/context to another by identifying common structural
patterns between distinct game contexts. This mirrors how humans transfer
learning across contexts (e.g., learning to drive helps with piloting).

The engine treats skills as transferable artifacts. It maintains a
registry of agent skills, a library of inter-domain mappings, and a
lifecycle of transfer tasks that progress from PENDING through ANALYZING
to TRANSFERRED, ADAPTED, or FAILED. Transfers are driven by four
strategies: ANALOGY, MAPPING, ABSTRACTION, and DECOMPOSITION.

Architecture:
  SkillTransferEngine (Singleton)
    |-- SkillRecord (a learned skill owned by an agent)
    |-- DomainMapping (structural bridge between two game domains)
    |-- TransferTask (a single cross-domain transfer lifecycle)
    |-- TransferStats / TransferSnapshot (aggregate observability)
    |-- TransferEvent (auditable event stream for handler dispatch)

Core Capabilities:
  - register_skill / get_skill / list_skills / remove_skill
  - create_mapping / get_mapping / list_mappings / remove_mapping
  - compute_similarity (estimate structural overlap between domains)
  - start_transfer / complete_transfer / fail_transfer (lifecycle)
  - get_transfer / list_transfers / get_transfer_history
  - register_event_handler / unregister_event_handler / list_events
  - get_stats / get_status / get_snapshot / reset

Usage:
    engine = get_skill_transfer()
    skill = engine.register_skill(
        agent_id="agent_alpha",
        name="Sword Combat",
        domain=DomainType.COMBAT.value,
        proficiency=0.85,
    )
    engine.create_mapping(
        source_domain=DomainType.COMBAT.value,
        target_domain=DomainType.STRATEGY.value,
        similarity_score=0.72,
        shared_patterns=["timing", "resource_management"],
        strategy=TransferStrategy.MAPPING.value,
    )
    task = engine.start_transfer(
        agent_id="agent_alpha",
        source_skill_id=skill.id,
        target_domain=DomainType.STRATEGY.value,
        strategy=TransferStrategy.MAPPING.value,
    )
    completed = engine.complete_transfer(task.id, "Tactical Coordination")
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums (string-valued for JSON compatibility)
# ---------------------------------------------------------------------------


class TransferStatus(Enum):
    """Lifecycle status of a cross-domain transfer task."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    TRANSFERRED = "transferred"
    FAILED = "failed"
    ADAPTED = "adapted"


class DomainType(Enum):
    """Game domains between which skills can be transferred."""
    COMBAT = "combat"
    MOVEMENT = "movement"
    PUZZLE = "puzzle"
    SOCIAL = "social"
    CRAFTING = "crafting"
    EXPLORATION = "exploration"
    STRATEGY = "strategy"
    CUSTOM = "custom"


class TransferStrategy(Enum):
    """Strategy used to migrate a skill across domains."""
    ANALOGY = "analogy"
    MAPPING = "mapping"
    ABSTRACTION = "abstraction"
    DECOMPOSITION = "decomposition"


class TransferEventKind(Enum):
    """Events emitted by the skill transfer engine for listeners."""
    SKILL_REGISTERED = "skill_registered"
    MAPPING_CREATED = "mapping_created"
    TRANSFER_STARTED = "transfer_started"
    TRANSFER_COMPLETED = "transfer_completed"
    TRANSFER_FAILED = "transfer_failed"


# ---------------------------------------------------------------------------
# Pattern catalog used to estimate cross-domain structural overlap.
# ---------------------------------------------------------------------------

# Canonical structural patterns associated with each game domain. The
# overlap of these pattern sets is used by compute_similarity to estimate
# how readily a skill from one domain can be transferred to another.
_DOMAIN_PATTERN_CATALOG: Dict[DomainType, List[str]] = {
    DomainType.COMBAT: [
        "timing", "resource_management", "spatial_awareness", "risk_assessment",
        "reaction_speed", "target_prioritization", "feint_and_punish",
        "stance_transition",
    ],
    DomainType.MOVEMENT: [
        "spatial_awareness", "path_optimization", "momentum_control",
        "terrain_reading", "timing", "precision_input", "route_planning",
    ],
    DomainType.PUZZLE: [
        "pattern_recognition", "logical_deduction", "hypothesis_testing",
        "resource_management", "sequence_planning", "constraint_satisfaction",
    ],
    DomainType.SOCIAL: [
        "intent_inference", "reputation_tracking", "dialogue_branching",
        "empathy_modeling", "negotiation_strategy", "risk_assessment",
    ],
    DomainType.CRAFTING: [
        "resource_management", "recipe_composition", "quality_optimization",
        "tool_selection", "sequence_planning", "precision_input",
    ],
    DomainType.EXPLORATION: [
        "spatial_awareness", "path_optimization", "route_planning",
        "terrain_reading", "novelty_detection", "risk_assessment",
        "resource_management",
    ],
    DomainType.STRATEGY: [
        "timing", "resource_management", "risk_assessment", "target_prioritization",
        "sequence_planning", "hypothesis_testing", "negotiation_strategy",
    ],
    DomainType.CUSTOM: [],
}

# Strategies that transfer well between specific domain pairs. Used as a
# tie-breaker when multiple candidate strategies are available.
_PREFERRED_STRATEGY_BY_DOMAIN_PAIR: Dict[Tuple[str, str], TransferStrategy] = {
    (DomainType.COMBAT.value, DomainType.STRATEGY.value): TransferStrategy.MAPPING,
    (DomainType.MOVEMENT.value, DomainType.EXPLORATION.value): TransferStrategy.ABSTRACTION,
    (DomainType.PUZZLE.value, DomainType.CRAFTING.value): TransferStrategy.ANALOGY,
    (DomainType.SOCIAL.value, DomainType.STRATEGY.value): TransferStrategy.DECOMPOSITION,
    (DomainType.COMBAT.value, DomainType.MOVEMENT.value): TransferStrategy.ABSTRACTION,
    (DomainType.CRAFTING.value, DomainType.PUZZLE.value): TransferStrategy.ANALOGY,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SkillRecord:
    """A learned skill owned by an agent within a particular game domain."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    name: str = ""
    domain: DomainType = DomainType.CUSTOM
    proficiency: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "domain": self.domain.value,
            "proficiency": round(self.proficiency, 4),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class DomainMapping:
    """A structural bridge between a source and a target game domain.

    Captures the similarity score and the shared structural patterns that
    justify transferring skills between the two domains.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_domain: DomainType = DomainType.CUSTOM
    target_domain: DomainType = DomainType.CUSTOM
    similarity_score: float = 0.0
    shared_patterns: List[str] = field(default_factory=list)
    strategy: TransferStrategy = TransferStrategy.MAPPING
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_domain": self.source_domain.value,
            "target_domain": self.target_domain.value,
            "similarity_score": round(self.similarity_score, 4),
            "shared_patterns": list(self.shared_patterns),
            "strategy": self.strategy.value,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class TransferTask:
    """A single cross-domain transfer lifecycle for an agent skill."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    source_skill_id: str = ""
    target_domain: DomainType = DomainType.CUSTOM
    strategy: TransferStrategy = TransferStrategy.MAPPING
    status: TransferStatus = TransferStatus.PENDING
    similarity_score: float = 0.0
    shared_patterns: List[str] = field(default_factory=list)
    adaptation_notes: str = ""
    started_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    completed_at: Optional[str] = None
    result_skill_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "source_skill_id": self.source_skill_id,
            "target_domain": self.target_domain.value,
            "strategy": self.strategy.value,
            "status": self.status.value,
            "similarity_score": round(self.similarity_score, 4),
            "shared_patterns": list(self.shared_patterns),
            "adaptation_notes": self.adaptation_notes,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_skill_id": self.result_skill_id,
        }


@dataclass
class TransferStats:
    """Aggregate statistics across all transfer operations."""
    total_skills: int = 0
    total_mappings: int = 0
    total_transfers: int = 0
    successful_transfers: int = 0
    failed_transfers: int = 0
    avg_similarity: float = 0.0
    last_updated_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        success_rate = (
            self.successful_transfers / self.total_transfers
            if self.total_transfers > 0
            else 0.0
        )
        return {
            "total_skills": self.total_skills,
            "total_mappings": self.total_mappings,
            "total_transfers": self.total_transfers,
            "successful_transfers": self.successful_transfers,
            "failed_transfers": self.failed_transfers,
            "avg_similarity": round(self.avg_similarity, 4),
            "success_rate": round(success_rate, 4),
            "last_updated_at": self.last_updated_at,
        }


@dataclass
class TransferSnapshot:
    """Point-in-time snapshot of the skill transfer engine state."""
    agent_count: int = 0
    total_skills: int = 0
    total_mappings: int = 0
    total_transfers: int = 0
    stats: TransferStats = field(default_factory=TransferStats)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "total_skills": self.total_skills,
            "total_mappings": self.total_mappings,
            "total_transfers": self.total_transfers,
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class TransferEvent:
    """An internal event emitted by the engine for handler dispatch."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: TransferEventKind = TransferEventKind.SKILL_REGISTERED
    agent_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "agent_id": self.agent_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# SkillTransferEngine Singleton
# ---------------------------------------------------------------------------


class SkillTransferEngine:
    """Thread-safe singleton engine for cross-domain skill transfer.

    Maintains a registry of agent skills, a library of inter-domain
    mappings, and the lifecycle of transfer tasks. All public
    operations are guarded by a re-entrant lock so the engine can be
    driven safely from multiple game threads.

    Skills migrate from a source domain to a target domain when the two
    domains share structural patterns. The engine estimates that overlap
    with a lightweight pattern catalog and the explicit mappings agents
    register. Each transfer is recorded as a TransferTask that moves
    through PENDING -> ANALYZING -> {TRANSFERRED, ADAPTED, FAILED}.
    """

    _instance: Optional["SkillTransferEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Capacity caps for in-memory registries.
    _MAX_SKILLS: int = 5000
    _MAX_MAPPINGS: int = 2000
    _MAX_TRANSFERS: int = 3000
    _MAX_EVENTS: int = 2000

    # Tuning constants for similarity estimation.
    _MAPPING_WEIGHT: float = 0.7
    _CATALOG_WEIGHT: float = 0.3
    _MIN_TRANSFER_SIMILARITY: float = 0.1

    def __new__(cls) -> "SkillTransferEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SkillTransferEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized: bool = True

        # Core registries keyed by id.
        self._skills: Dict[str, SkillRecord] = {}
        self._mappings: Dict[str, DomainMapping] = {}
        self._transfers: Dict[str, TransferTask] = {}

        # Per-agent and per-domain indices for fast filtering.
        self._skills_by_agent: Dict[str, List[str]] = {}
        self._skills_by_domain: Dict[DomainType, List[str]] = {}
        self._mappings_by_source: Dict[DomainType, List[str]] = {}
        self._mappings_by_target: Dict[DomainType, List[str]] = {}
        self._transfers_by_agent: Dict[str, List[str]] = {}

        # Event system.
        self._events: List[TransferEvent] = []
        self._event_handlers: Dict[str, List[Tuple[str, Callable[[TransferEvent], None]]]] = {}

        # Aggregate counters.
        self._total_skills_registered: int = 0
        self._total_mappings_created: int = 0
        self._total_transfers_started: int = 0
        self._successful_transfers: int = 0
        self._failed_transfers: int = 0

        # Seed default demo data so the system works out of the box.
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate demo skills, domain mappings, and one completed transfer.

        This gives the engine immediately useful state so the read paths
        can be exercised without further configuration.
        """
        self._seed_agent_alpha()
        self._seed_agent_beta()
        self._seed_domain_mappings()
        self._seed_completed_transfer()

    def _seed_agent_alpha(self) -> None:
        """Seed four cross-domain skills for agent_alpha."""
        alpha_skills = [
            ("Sword Combat", DomainType.COMBAT, 0.85, {"weapon": "longsword", "tier": 2}),
            ("Parkour Movement", DomainType.MOVEMENT, 0.75, {"terrain": "urban"}),
            ("Lock Picking", DomainType.PUZZLE, 0.6, {"complexity": "medium"}),
            ("Diplomatic Negotiation", DomainType.SOCIAL, 0.7, {"stance": "neutral"}),
        ]
        for name, domain, proficiency, meta in alpha_skills:
            self._register_skill_internal(
                agent_id="agent_alpha",
                name=name,
                domain=domain,
                proficiency=proficiency,
                metadata=dict(meta),
            )

    def _seed_agent_beta(self) -> None:
        """Seed two skills for agent_beta."""
        beta_skills = [
            ("Spell Casting", DomainType.COMBAT, 0.8, {"school": "evocation"}),
            ("Terrain Navigation", DomainType.EXPLORATION, 0.65, {"biome": "forest"}),
        ]
        for name, domain, proficiency, meta in beta_skills:
            self._register_skill_internal(
                agent_id="agent_beta",
                name=name,
                domain=domain,
                proficiency=proficiency,
                metadata=dict(meta),
            )

    def _seed_domain_mappings(self) -> None:
        """Seed two structural bridges between game domains."""
        self._create_mapping_internal(
            source_domain=DomainType.COMBAT,
            target_domain=DomainType.STRATEGY,
            similarity_score=0.72,
            shared_patterns=["timing", "resource_management"],
            strategy=TransferStrategy.MAPPING,
            metadata={"seeded": True, "rationale": "combat tempo informs strategic planning"},
        )
        self._create_mapping_internal(
            source_domain=DomainType.MOVEMENT,
            target_domain=DomainType.EXPLORATION,
            similarity_score=0.81,
            shared_patterns=["spatial_awareness", "path_optimization"],
            strategy=TransferStrategy.ABSTRACTION,
            metadata={"seeded": True, "rationale": "movement skills generalize to exploration"},
        )

    def _seed_completed_transfer(self) -> None:
        """Seed one completed transfer: agent_alpha combat -> strategy."""
        # Locate the seeded "Sword Combat" skill for agent_alpha.
        source_skill_id: Optional[str] = None
        for sid in self._skills_by_agent.get("agent_alpha", []):
            skill = self._skills.get(sid)
            if skill is not None and skill.name == "Sword Combat":
                source_skill_id = sid
                break
        if source_skill_id is None:
            return

        task = TransferTask(
            agent_id="agent_alpha",
            source_skill_id=source_skill_id,
            target_domain=DomainType.STRATEGY,
            strategy=TransferStrategy.MAPPING,
            status=TransferStatus.PENDING,
            similarity_score=0.72,
            shared_patterns=["timing", "resource_management"],
            started_at=datetime.datetime.utcnow().isoformat() + "Z",
        )
        self._transfers[task.id] = task
        self._transfers_by_agent.setdefault(task.agent_id, []).append(task.id)
        self._total_transfers_started += 1

        # Register the resulting transferred skill in the strategy domain.
        result_skill = self._register_skill_internal(
            agent_id="agent_alpha",
            name="Tactical Coordination",
            domain=DomainType.STRATEGY,
            proficiency=0.66,
            metadata={
                "transferred_from": source_skill_id,
                "transfer_task": task.id,
                "seeded": True,
            },
        )

        task.status = TransferStatus.TRANSFERRED
        task.completed_at = datetime.datetime.utcnow().isoformat() + "Z"
        task.result_skill_id = result_skill.id
        task.adaptation_notes = (
            "Adapted sword-fight tempo discipline into squad-level tactical timing."
        )
        self._successful_transfers += 1

        # Emit the corresponding lifecycle events without re-entrancy concerns.
        self._events.append(TransferEvent(
            kind=TransferEventKind.TRANSFER_STARTED,
            agent_id=task.agent_id,
            payload={"task_id": task.id, "source_skill_id": source_skill_id},
        ))
        self._events.append(TransferEvent(
            kind=TransferEventKind.TRANSFER_COMPLETED,
            agent_id=task.agent_id,
            payload={"task_id": task.id, "result_skill_id": result_skill.id},
        ))
        self._trim_events()

    # ------------------------------------------------------------------
    # Internal helpers (lock assumed held)
    # ------------------------------------------------------------------

    def _now(self) -> str:
        """Return the current UTC timestamp in ISO-8601 with a Z suffix."""
        return datetime.datetime.utcnow().isoformat() + "Z"

    def _emit_event(
        self,
        kind: TransferEventKind,
        agent_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TransferEvent:
        """Create, store, and dispatch an event to registered handlers."""
        event = TransferEvent(
            kind=kind,
            agent_id=agent_id,
            payload=payload if payload is not None else {},
        )
        self._events.append(event)
        self._trim_events()
        for handler_id, handler in self._event_handlers.get(kind.value, []):
            try:
                handler(event)
            except Exception:
                # Handler errors must not disrupt engine operation.
                pass
        return event

    def _trim_events(self) -> None:
        """Enforce the in-memory event cap, keeping the most recent events."""
        if len(self._events) > self._MAX_EVENTS:
            self._events = self._events[-self._MAX_EVENTS:]

    def _trim_skills(self) -> None:
        """Enforce the skill cap by evicting the oldest records."""
        if len(self._skills) <= self._MAX_SKILLS:
            return
        overflow = len(self._skills) - self._MAX_SKILLS
        oldest_ids = sorted(
            self._skills.keys(),
            key=lambda sid: self._skills[sid].timestamp,
        )[:overflow]
        for sid in oldest_ids:
            self._remove_skill_internal(sid)

    def _trim_mappings(self) -> None:
        """Enforce the mapping cap by evicting the oldest mappings."""
        if len(self._mappings) <= self._MAX_MAPPINGS:
            return
        overflow = len(self._mappings) - self._MAX_MAPPINGS
        oldest_ids = sorted(
            self._mappings.keys(),
            key=lambda mid: self._mappings[mid].timestamp,
        )[:overflow]
        for mid in oldest_ids:
            self._remove_mapping_internal(mid)

    def _trim_transfers(self) -> None:
        """Enforce the transfer cap by evicting the oldest tasks."""
        if len(self._transfers) <= self._MAX_TRANSFERS:
            return
        overflow = len(self._transfers) - self._MAX_TRANSFERS
        oldest_ids = sorted(
            self._transfers.keys(),
            key=lambda tid: self._transfers[tid].started_at,
        )[:overflow]
        for tid in oldest_ids:
            self._remove_transfer_internal(tid)

    def _register_skill_internal(
        self,
        agent_id: str,
        name: str,
        domain: DomainType,
        proficiency: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SkillRecord:
        """Create and store a skill record. Lock must already be held."""
        skill = SkillRecord(
            agent_id=agent_id,
            name=name,
            domain=domain,
            proficiency=max(0.0, min(1.0, proficiency)),
            metadata=dict(metadata) if metadata else {},
        )
        self._skills[skill.id] = skill
        self._skills_by_agent.setdefault(agent_id, []).append(skill.id)
        self._skills_by_domain.setdefault(domain, []).append(skill.id)
        self._total_skills_registered += 1
        self._trim_skills()
        return skill

    def _remove_skill_internal(self, skill_id: str) -> bool:
        """Remove a skill from all indices. Lock must already be held."""
        skill = self._skills.pop(skill_id, None)
        if skill is None:
            return False
        agent_ids = self._skills_by_agent.get(skill.agent_id, [])
        if skill_id in agent_ids:
            agent_ids.remove(skill_id)
            if not agent_ids:
                self._skills_by_agent.pop(skill.agent_id, None)
        domain_ids = self._skills_by_domain.get(skill.domain, [])
        if skill_id in domain_ids:
            domain_ids.remove(skill_id)
            if not domain_ids:
                self._skills_by_domain.pop(skill.domain, None)
        return True

    def _create_mapping_internal(
        self,
        source_domain: DomainType,
        target_domain: DomainType,
        similarity_score: float,
        shared_patterns: List[str],
        strategy: TransferStrategy,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DomainMapping:
        """Create and store a domain mapping. Lock must already be held."""
        mapping = DomainMapping(
            source_domain=source_domain,
            target_domain=target_domain,
            similarity_score=max(0.0, min(1.0, similarity_score)),
            shared_patterns=list(shared_patterns),
            strategy=strategy,
            metadata=dict(metadata) if metadata else {},
        )
        self._mappings[mapping.id] = mapping
        self._mappings_by_source.setdefault(source_domain, []).append(mapping.id)
        self._mappings_by_target.setdefault(target_domain, []).append(mapping.id)
        self._total_mappings_created += 1
        self._trim_mappings()
        return mapping

    def _remove_mapping_internal(self, mapping_id: str) -> bool:
        """Remove a mapping from all indices. Lock must already be held."""
        mapping = self._mappings.pop(mapping_id, None)
        if mapping is None:
            return False
        source_ids = self._mappings_by_source.get(mapping.source_domain, [])
        if mapping_id in source_ids:
            source_ids.remove(mapping_id)
            if not source_ids:
                self._mappings_by_source.pop(mapping.source_domain, None)
        target_ids = self._mappings_by_target.get(mapping.target_domain, [])
        if mapping_id in target_ids:
            target_ids.remove(mapping_id)
            if not target_ids:
                self._mappings_by_target.pop(mapping.target_domain, None)
        return True

    def _remove_transfer_internal(self, transfer_id: str) -> bool:
        """Remove a transfer task from all indices. Lock must already be held."""
        task = self._transfers.pop(transfer_id, None)
        if task is None:
            return False
        agent_ids = self._transfers_by_agent.get(task.agent_id, [])
        if transfer_id in agent_ids:
            agent_ids.remove(transfer_id)
            if not agent_ids:
                self._transfers_by_agent.pop(task.agent_id, None)
        return True

    def _resolve_domain(self, domain: str) -> DomainType:
        """Parse a domain string into a DomainType, defaulting to CUSTOM."""
        try:
            return DomainType(domain)
        except ValueError:
            return DomainType.CUSTOM

    def _resolve_strategy(self, strategy: Optional[str]) -> TransferStrategy:
        """Parse a strategy string into a TransferStrategy, defaulting to MAPPING."""
        if strategy is None:
            return TransferStrategy.MAPPING
        try:
            return TransferStrategy(strategy)
        except ValueError:
            return TransferStrategy.MAPPING

    def _catalog_patterns(self, domain: DomainType) -> List[str]:
        """Return the canonical structural patterns for a domain."""
        return list(_DOMAIN_PATTERN_CATALOG.get(domain, []))

    def _best_mapping_for(
        self,
        source_domain: DomainType,
        target_domain: DomainType,
    ) -> Optional[DomainMapping]:
        """Return the highest-similarity explicit mapping between two domains."""
        candidates: List[DomainMapping] = []
        for mid in self._mappings_by_source.get(source_domain, []):
            mapping = self._mappings.get(mid)
            if mapping is not None and mapping.target_domain == target_domain:
                candidates.append(mapping)
        if not candidates:
            return None
        candidates.sort(key=lambda m: m.similarity_score, reverse=True)
        return candidates[0]

    # ------------------------------------------------------------------
    # Skill management
    # ------------------------------------------------------------------

    def register_skill(
        self,
        agent_id: str,
        name: str,
        domain: str,
        proficiency: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SkillRecord:
        """Register a learned skill for an agent.

        Args:
            agent_id: The owning agent.
            name: Human-readable skill name.
            domain: One of DomainType's string values.
            proficiency: Skill proficiency in [0, 1].
            metadata: Optional free-form metadata.

        Returns:
            The newly registered SkillRecord.
        """
        with self._lock:
            domain_enum = self._resolve_domain(domain)
            skill = self._register_skill_internal(
                agent_id=agent_id,
                name=name,
                domain=domain_enum,
                proficiency=proficiency,
                metadata=metadata,
            )
            self._emit_event(
                TransferEventKind.SKILL_REGISTERED,
                agent_id=agent_id,
                payload={"skill_id": skill.id, "name": name, "domain": domain_enum.value},
            )
            return skill

    def get_skill(self, skill_id: str) -> Optional[SkillRecord]:
        """Return a skill by id, or None if not found."""
        with self._lock:
            return self._skills.get(skill_id)

    def list_skills(
        self,
        agent_id: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[SkillRecord]:
        """List skills, optionally filtered by agent and/or domain.

        Args:
            agent_id: When provided, restrict to skills owned by this agent.
            domain: When provided, restrict to skills in this domain.

        Returns:
            A list of matching SkillRecord instances.
        """
        with self._lock:
            if agent_id is not None:
                candidate_ids = list(self._skills_by_agent.get(agent_id, []))
            elif domain is not None:
                domain_enum = self._resolve_domain(domain)
                candidate_ids = list(self._skills_by_domain.get(domain_enum, []))
            else:
                candidate_ids = list(self._skills.keys())

            results: List[SkillRecord] = []
            for sid in candidate_ids:
                skill = self._skills.get(sid)
                if skill is None:
                    continue
                if agent_id is not None and skill.agent_id != agent_id:
                    continue
                if domain is not None:
                    domain_enum = self._resolve_domain(domain)
                    if skill.domain != domain_enum:
                        continue
                results.append(skill)
            results.sort(key=lambda s: s.timestamp)
            return results

    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill by id.

        Args:
            skill_id: The skill to remove.

        Returns:
            True if the skill was removed, False if it did not exist.
        """
        with self._lock:
            return self._remove_skill_internal(skill_id)

    # ------------------------------------------------------------------
    # Domain mapping management
    # ------------------------------------------------------------------

    def create_mapping(
        self,
        source_domain: str,
        target_domain: str,
        similarity_score: float,
        shared_patterns: List[str],
        strategy: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DomainMapping:
        """Create a structural mapping between two game domains.

        Args:
            source_domain: The domain skills migrate from.
            target_domain: The domain skills migrate to.
            similarity_score: Structural overlap in [0, 1].
            shared_patterns: Structural patterns the two domains share.
            strategy: One of TransferStrategy's string values.
            metadata: Optional free-form metadata.

        Returns:
            The newly created DomainMapping.
        """
        with self._lock:
            source_enum = self._resolve_domain(source_domain)
            target_enum = self._resolve_domain(target_domain)
            strategy_enum = self._resolve_strategy(strategy)
            mapping = self._create_mapping_internal(
                source_domain=source_enum,
                target_domain=target_enum,
                similarity_score=similarity_score,
                shared_patterns=shared_patterns,
                strategy=strategy_enum,
                metadata=metadata,
            )
            self._emit_event(
                TransferEventKind.MAPPING_CREATED,
                payload={
                    "mapping_id": mapping.id,
                    "source_domain": source_enum.value,
                    "target_domain": target_enum.value,
                    "similarity_score": round(mapping.similarity_score, 4),
                },
            )
            return mapping

    def get_mapping(self, mapping_id: str) -> Optional[DomainMapping]:
        """Return a domain mapping by id, or None if not found."""
        with self._lock:
            return self._mappings.get(mapping_id)

    def list_mappings(
        self,
        source_domain: Optional[str] = None,
        target_domain: Optional[str] = None,
    ) -> List[DomainMapping]:
        """List domain mappings, optionally filtered by source and/or target.

        Args:
            source_domain: When provided, restrict to mappings from this domain.
            target_domain: When provided, restrict to mappings to this domain.

        Returns:
            A list of matching DomainMapping instances.
        """
        with self._lock:
            if source_domain is not None and target_domain is not None:
                source_enum = self._resolve_domain(source_domain)
                target_enum = self._resolve_domain(target_domain)
                candidate_ids = [
                    mid for mid in self._mappings_by_source.get(source_enum, [])
                    if self._mappings.get(mid) is not None
                    and self._mappings[mid].target_domain == target_enum
                ]
            elif source_domain is not None:
                source_enum = self._resolve_domain(source_domain)
                candidate_ids = list(self._mappings_by_source.get(source_enum, []))
            elif target_domain is not None:
                target_enum = self._resolve_domain(target_domain)
                candidate_ids = list(self._mappings_by_target.get(target_enum, []))
            else:
                candidate_ids = list(self._mappings.keys())

            results: List[DomainMapping] = []
            for mid in candidate_ids:
                mapping = self._mappings.get(mid)
                if mapping is None:
                    continue
                if source_domain is not None:
                    source_enum = self._resolve_domain(source_domain)
                    if mapping.source_domain != source_enum:
                        continue
                if target_domain is not None:
                    target_enum = self._resolve_domain(target_domain)
                    if mapping.target_domain != target_enum:
                        continue
                results.append(mapping)
            results.sort(key=lambda m: m.similarity_score, reverse=True)
            return results

    def remove_mapping(self, mapping_id: str) -> bool:
        """Remove a domain mapping by id.

        Args:
            mapping_id: The mapping to remove.

        Returns:
            True if the mapping was removed, False if it did not exist.
        """
        with self._lock:
            return self._remove_mapping_internal(mapping_id)

    # ------------------------------------------------------------------
    # Similarity computation
    # ------------------------------------------------------------------

    def compute_similarity(
        self,
        source_skill_id: str,
        target_domain: str,
    ) -> Dict[str, Any]:
        """Estimate structural overlap between a skill's domain and a target.

        The estimate blends the best explicit DomainMapping (if any) with a
        catalog-based Jaccard overlap of canonical structural patterns.

        Args:
            source_skill_id: The skill whose domain is the source.
            target_domain: The domain skills would migrate to.

        Returns:
            A dict with similarity_score, shared_patterns, strategy,
            mapping_id, source_domain, and target_domain fields. A
            similarity of 0.0 is returned when the skill is unknown.
        """
        with self._lock:
            skill = self._skills.get(source_skill_id)
            if skill is None:
                return {
                    "similarity_score": 0.0,
                    "shared_patterns": [],
                    "strategy": TransferStrategy.MAPPING.value,
                    "mapping_id": None,
                    "source_domain": None,
                    "target_domain": target_domain,
                    "skill_id": source_skill_id,
                }

            source_domain = skill.domain
            target_enum = self._resolve_domain(target_domain)

            # Explicit mapping takes priority when available.
            mapping = self._best_mapping_for(source_domain, target_enum)
            if mapping is not None:
                similarity = mapping.similarity_score
                shared = list(mapping.shared_patterns)
                strategy = mapping.strategy
                mapping_id = mapping.id
            else:
                # Fall back to a catalog-based Jaccard overlap.
                source_patterns = set(self._catalog_patterns(source_domain))
                target_patterns = set(self._catalog_patterns(target_enum))
                if not source_patterns or not target_patterns:
                    similarity = 0.0
                    shared = []
                else:
                    intersection = source_patterns & target_patterns
                    union = source_patterns | target_patterns
                    similarity = len(intersection) / len(union) if union else 0.0
                    shared = sorted(intersection)
                strategy = _PREFERRED_STRATEGY_BY_DOMAIN_PAIR.get(
                    (source_domain.value, target_enum.value),
                    TransferStrategy.ABSTRACTION,
                )
                mapping_id = None

            similarity = max(similarity, self._MIN_TRANSFER_SIMILARITY) if shared else similarity

            return {
                "similarity_score": round(similarity, 4),
                "shared_patterns": shared,
                "strategy": strategy.value,
                "mapping_id": mapping_id,
                "source_domain": source_domain.value,
                "target_domain": target_enum.value,
                "skill_id": source_skill_id,
            }

    # ------------------------------------------------------------------
    # Transfer lifecycle
    # ------------------------------------------------------------------

    def start_transfer(
        self,
        agent_id: str,
        source_skill_id: str,
        target_domain: str,
        strategy: Optional[str] = None,
    ) -> TransferTask:
        """Start a cross-domain transfer task for a skill.

        Computes the similarity between the skill's source domain and the
        target domain, then records a TransferTask in PENDING/ANALYZING
        state. When no strategy is supplied, the strategy suggested by
        compute_similarity is used.

        Args:
            agent_id: The agent that owns the skill.
            source_skill_id: The skill to transfer.
            target_domain: The destination domain.
            strategy: Optional explicit TransferStrategy string value.

        Returns:
            The newly created TransferTask.
        """
        with self._lock:
            skill = self._skills.get(source_skill_id)
            if skill is None:
                # Record a failed transfer so callers can inspect the reason.
                task = TransferTask(
                    agent_id=agent_id,
                    source_skill_id=source_skill_id,
                    target_domain=self._resolve_domain(target_domain),
                    strategy=self._resolve_strategy(strategy),
                    status=TransferStatus.FAILED,
                    similarity_score=0.0,
                    adaptation_notes=(
                        f"Source skill {source_skill_id} not found; "
                        "transfer cannot proceed."
                    ),
                    started_at=self._now(),
                    completed_at=self._now(),
                )
                self._transfers[task.id] = task
                self._transfers_by_agent.setdefault(agent_id, []).append(task.id)
                self._total_transfers_started += 1
                self._failed_transfers += 1
                self._trim_transfers()
                self._emit_event(
                    TransferEventKind.TRANSFER_FAILED,
                    agent_id=agent_id,
                    payload={"task_id": task.id, "reason": "source_skill_not_found"},
                )
                return task

            similarity = self.compute_similarity(source_skill_id, target_domain)
            strategy_enum = self._resolve_strategy(strategy)
            if strategy is None:
                strategy_enum = self._resolve_strategy(similarity["strategy"])

            task = TransferTask(
                agent_id=agent_id,
                source_skill_id=source_skill_id,
                target_domain=self._resolve_domain(target_domain),
                strategy=strategy_enum,
                status=TransferStatus.ANALYZING,
                similarity_score=float(similarity["similarity_score"]),
                shared_patterns=list(similarity["shared_patterns"]),
                started_at=self._now(),
            )
            self._transfers[task.id] = task
            self._transfers_by_agent.setdefault(agent_id, []).append(task.id)
            self._total_transfers_started += 1
            self._trim_transfers()
            self._emit_event(
                TransferEventKind.TRANSFER_STARTED,
                agent_id=agent_id,
                payload={
                    "task_id": task.id,
                    "source_skill_id": source_skill_id,
                    "target_domain": task.target_domain.value,
                    "similarity_score": round(task.similarity_score, 4),
                },
            )
            return task

    def complete_transfer(
        self,
        task_id: str,
        result_skill_name: str,
        adaptation_notes: str = "",
    ) -> Optional[TransferTask]:
        """Complete a transfer task, producing a new skill in the target domain.

        The source skill's proficiency is scaled by the similarity score to
        produce the transferred skill's proficiency. When adaptation notes
        are provided, the task is marked ADAPTED; otherwise TRANSFERRED.

        Args:
            task_id: The transfer task to complete.
            result_skill_name: Name for the resulting skill.
            adaptation_notes: Notes on how the skill was adapted.

        Returns:
            The updated TransferTask, or None if the task was not found or
            was not in a completable state.
        """
        with self._lock:
            task = self._transfers.get(task_id)
            if task is None:
                return None
            if task.status in (TransferStatus.TRANSFERRED, TransferStatus.ADAPTED):
                return task
            if task.status == TransferStatus.FAILED:
                return None

            source_skill = self._skills.get(task.source_skill_id)
            base_proficiency = source_skill.proficiency if source_skill else 0.0
            transferred_proficiency = base_proficiency * max(0.0, min(1.0, task.similarity_score))

            result_skill = self._register_skill_internal(
                agent_id=task.agent_id,
                name=result_skill_name,
                domain=task.target_domain,
                proficiency=transferred_proficiency,
                metadata={
                    "transferred_from": task.source_skill_id,
                    "transfer_task": task.id,
                    "transfer_strategy": task.strategy.value,
                    "shared_patterns": list(task.shared_patterns),
                },
            )

            task.status = (
                TransferStatus.ADAPTED if adaptation_notes else TransferStatus.TRANSFERRED
            )
            task.completed_at = self._now()
            task.result_skill_id = result_skill.id
            task.adaptation_notes = adaptation_notes
            self._successful_transfers += 1

            self._emit_event(
                TransferEventKind.TRANSFER_COMPLETED,
                agent_id=task.agent_id,
                payload={
                    "task_id": task.id,
                    "result_skill_id": result_skill.id,
                    "status": task.status.value,
                },
            )
            return task

    def fail_transfer(
        self,
        task_id: str,
        reason: str,
    ) -> Optional[TransferTask]:
        """Mark a transfer task as failed.

        Args:
            task_id: The transfer task to fail.
            reason: Human-readable reason for the failure.

        Returns:
            The updated TransferTask, or None if the task was not found.
        """
        with self._lock:
            task = self._transfers.get(task_id)
            if task is None:
                return None
            if task.status in (TransferStatus.TRANSFERRED, TransferStatus.ADAPTED):
                return task

            task.status = TransferStatus.FAILED
            task.completed_at = self._now()
            task.adaptation_notes = reason
            self._failed_transfers += 1

            self._emit_event(
                TransferEventKind.TRANSFER_FAILED,
                agent_id=task.agent_id,
                payload={"task_id": task.id, "reason": reason},
            )
            return task

    def get_transfer(self, task_id: str) -> Optional[TransferTask]:
        """Return a transfer task by id, or None if not found."""
        with self._lock:
            return self._transfers.get(task_id)

    def list_transfers(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[TransferTask]:
        """List transfer tasks, optionally filtered by agent and/or status.

        Args:
            agent_id: When provided, restrict to tasks for this agent.
            status: When provided, restrict to tasks in this status.

        Returns:
            A list of matching TransferTask instances.
        """
        with self._lock:
            if agent_id is not None:
                candidate_ids = list(self._transfers_by_agent.get(agent_id, []))
            else:
                candidate_ids = list(self._transfers.keys())

            status_enum: Optional[TransferStatus] = None
            if status is not None:
                try:
                    status_enum = TransferStatus(status)
                except ValueError:
                    status_enum = None

            results: List[TransferTask] = []
            for tid in candidate_ids:
                task = self._transfers.get(tid)
                if task is None:
                    continue
                if status_enum is not None and task.status != status_enum:
                    continue
                results.append(task)
            results.sort(key=lambda t: t.started_at, reverse=True)
            return results

    def get_transfer_history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return the recent transfer history for an agent as a list of dicts.

        Args:
            agent_id: The agent whose history to return.
            limit: Maximum number of records to return.

        Returns:
            A list of transfer task dictionaries, most recent first.
        """
        with self._lock:
            candidate_ids = list(self._transfers_by_agent.get(agent_id, []))
            tasks: List[TransferTask] = []
            for tid in candidate_ids:
                task = self._transfers.get(tid)
                if task is not None:
                    tasks.append(task)
            tasks.sort(key=lambda t: t.started_at, reverse=True)
            return [t.to_dict() for t in tasks[:max(0, limit)]]

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: TransferEventKind,
        handler: Callable[[TransferEvent], None],
    ) -> str:
        """Register a handler for a specific event kind.

        Args:
            kind: The TransferEventKind to listen for.
            handler: Callable invoked with each matching event.

        Returns:
            A handler id that uniquely identifies the registration.
        """
        with self._lock:
            handler_id = uuid.uuid4().hex
            self._event_handlers.setdefault(kind.value, []).append((handler_id, handler))
            return handler_id

    def unregister_event_handler(self, handler_id: str) -> bool:
        """Unregister a previously registered event handler.

        Args:
            handler_id: The id returned by register_event_handler.

        Returns:
            True if a handler was removed, False otherwise.
        """
        with self._lock:
            for kind, handlers in self._event_handlers.items():
                for idx, (hid, _) in enumerate(handlers):
                    if hid == handler_id:
                        handlers.pop(idx)
                        if not handlers:
                            self._event_handlers.pop(kind, None)
                        return True
            return False

    def list_events(
        self,
        event_kind: Optional[TransferEventKind] = None,
        limit: int = 100,
    ) -> List[TransferEvent]:
        """Return recent events, optionally filtered by kind.

        Args:
            event_kind: When provided, restrict to events of this kind.
            limit: Maximum number of events to return.

        Returns:
            A list of matching TransferEvent instances.
        """
        with self._lock:
            events = list(self._events)
            if event_kind is not None:
                events = [e for e in events if e.kind == event_kind]
            return events[-max(0, limit):]

    # ------------------------------------------------------------------
    # Statistics and observability
    # ------------------------------------------------------------------

    def get_stats(self) -> TransferStats:
        """Return aggregate statistics across the engine."""
        with self._lock:
            similarity_scores = [t.similarity_score for t in self._transfers.values()]
            avg_similarity = (
                sum(similarity_scores) / len(similarity_scores)
                if similarity_scores else 0.0
            )
            return TransferStats(
                total_skills=len(self._skills),
                total_mappings=len(self._mappings),
                total_transfers=len(self._transfers),
                successful_transfers=self._successful_transfers,
                failed_transfers=self._failed_transfers,
                avg_similarity=avg_similarity,
                last_updated_at=self._now(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a dictionary with current engine statistics."""
        with self._lock:
            domain_counts: Dict[str, int] = {}
            for skill in self._skills.values():
                key = skill.domain.value
                domain_counts[key] = domain_counts.get(key, 0) + 1

            status_counts: Dict[str, int] = {}
            for task in self._transfers.values():
                key = task.status.value
                status_counts[key] = status_counts.get(key, 0) + 1

            similarity_scores = [t.similarity_score for t in self._transfers.values()]
            avg_similarity = (
                sum(similarity_scores) / len(similarity_scores)
                if similarity_scores else 0.0
            )

            return {
                "initialized": self._initialized,
                "total_skills": len(self._skills),
                "total_skills_registered": self._total_skills_registered,
                "total_mappings": len(self._mappings),
                "total_mappings_created": self._total_mappings_created,
                "total_transfers": len(self._transfers),
                "total_transfers_started": self._total_transfers_started,
                "successful_transfers": self._successful_transfers,
                "failed_transfers": self._failed_transfers,
                "avg_similarity": round(avg_similarity, 4),
                "total_events": len(self._events),
                "agent_count": len(self._skills_by_agent),
                "domain_distribution": domain_counts,
                "status_distribution": status_counts,
                "max_skills": self._MAX_SKILLS,
                "max_mappings": self._MAX_MAPPINGS,
                "max_transfers": self._MAX_TRANSFERS,
                "max_events": self._MAX_EVENTS,
            }

    def get_snapshot(self) -> TransferSnapshot:
        """Return a point-in-time snapshot of the engine state."""
        with self._lock:
            return TransferSnapshot(
                agent_count=len(self._skills_by_agent),
                total_skills=len(self._skills),
                total_mappings=len(self._mappings),
                total_transfers=len(self._transfers),
                stats=self.get_stats(),
                timestamp=self._now(),
            )

    def reset(self) -> None:
        """Clear all stored data and re-seed the default demo state."""
        with self._lock:
            self._skills.clear()
            self._mappings.clear()
            self._transfers.clear()
            self._skills_by_agent.clear()
            self._skills_by_domain.clear()
            self._mappings_by_source.clear()
            self._mappings_by_target.clear()
            self._transfers_by_agent.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._total_skills_registered = 0
            self._total_mappings_created = 0
            self._total_transfers_started = 0
            self._successful_transfers = 0
            self._failed_transfers = 0
            self._seed_default_data()


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------


def get_skill_transfer() -> SkillTransferEngine:
    """Get or create the global SkillTransferEngine singleton."""
    return SkillTransferEngine.get_instance()
