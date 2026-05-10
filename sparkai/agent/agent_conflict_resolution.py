"""
SparkLabs Agent - Conflict Resolution Engine

Intelligent mediation for resolving contradictory outputs across
multiple agent subsystems. When competing agents propose conflicting
game design choices, asset modifications, or engine configurations,
the resolution engine employs negotiation strategies to converge
on coherent AI-native game development decisions.

Architecture:
  ConflictResolutionEngine
    |-- ConflictDetector (identifying contradictory agent outputs)
    |-- ResolutionStrategy (mediation approach selection)
    |-- PriorityResolver (agent authority-weighted arbitration)
    |-- MergeEngine (combining compatible partial solutions)
    |-- EscalationManager (unresolvable conflict handling)
    |-- ResolutionLog (audit trail of decisions made)

Strategies:
  - PRIORITY: higher-priority agent wins
  - MERGE: combine non-overlapping portions of proposals
  - VOTE: democratic resolution via consensus call
  - ROLLBACK: revert to last known consistent state
  - DEFER: escalate to human operator
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConflictType(Enum):
    VALUE = "value"
    STRUCTURE = "structure"
    SEQUENCE = "sequence"
    OWNERSHIP = "ownership"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"


class ResolutionStrategy(Enum):
    PRIORITY = "priority"
    MERGE = "merge"
    VOTE = "vote"
    ROLLBACK = "rollback"
    DEFER = "defer"


class ResolutionStatus(Enum):
    DETECTED = "detected"
    ANALYZING = "analyzing"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    ESCALATED = "escalated"
    UNRESOLVABLE = "unresolvable"


@dataclass
class ConflictProposal:
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    domain: str = ""
    key: str = ""
    proposed_value: Any = None
    rationale: str = ""
    confidence: float = 0.5
    priority: int = 1
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "domain": self.domain,
            "key": self.key,
            "value": str(self.proposed_value),
            "confidence": self.confidence,
            "priority": self.priority,
        }


@dataclass
class ConflictCase:
    case_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    conflict_type: ConflictType = ConflictType.VALUE
    domain: str = ""
    key: str = ""
    proposals: List[ConflictProposal] = field(default_factory=list)
    status: ResolutionStatus = ResolutionStatus.DETECTED
    resolved_value: Any = None
    resolution_strategy: Optional[ResolutionStrategy] = None
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "type": self.conflict_type.value,
            "domain": self.domain,
            "key": self.key,
            "proposal_count": len(self.proposals),
            "status": self.status.value,
            "strategy": self.resolution_strategy.value if self.resolution_strategy else None,
        }


@dataclass
class ResolutionLog:
    log_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    case_id: str = ""
    strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY
    winner_agent: str = ""
    explanation: str = ""
    timestamp: float = field(default_factory=time.time)


class ConflictResolutionEngine:
    _instance: Optional[ConflictResolutionEngine] = None

    @classmethod
    def get_instance(cls) -> ConflictResolutionEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._active_conflicts: Dict[str, ConflictCase] = {}
        self._resolution_log: List[ResolutionLog] = []
        self._agent_priorities: Dict[str, int] = {}
        self._domain_default_strategies: Dict[str, ResolutionStrategy] = {
            "scene": ResolutionStrategy.MERGE,
            "asset": ResolutionStrategy.PRIORITY,
            "code": ResolutionStrategy.ROLLBACK,
            "config": ResolutionStrategy.VOTE,
            "narrative": ResolutionStrategy.DEFER,
        }
        self._total_resolved: int = 0

    def set_agent_priority(self, agent_id: str, priority: int):
        self._agent_priorities[agent_id] = priority

    def detect_conflict(self, domain: str, key: str, proposals: List[ConflictProposal]) -> Optional[ConflictCase]:
        unique_values = set(str(p.proposed_value) for p in proposals)
        if len(unique_values) <= 1:
            return None
        conflict_type = ConflictType.VALUE
        if domain in ("scene", "structure"):
            conflict_type = ConflictType.STRUCTURE
        case = ConflictCase(
            conflict_type=conflict_type,
            domain=domain,
            key=key,
            proposals=proposals,
            status=ResolutionStatus.DETECTED,
        )
        self._active_conflicts[case.case_id] = case
        return case

    async def resolve(self, case_id: str, strategy: Optional[ResolutionStrategy] = None) -> ConflictCase:
        case = self._active_conflicts.get(case_id)
        if case is None:
            raise ValueError(f"Conflict case not found: {case_id}")

        strategy = strategy or self._domain_default_strategies.get(case.domain, ResolutionStrategy.PRIORITY)
        case.status = ResolutionStatus.ANALYZING
        case.resolution_strategy = strategy

        if strategy == ResolutionStrategy.PRIORITY:
            sorted_proposals = sorted(case.proposals, key=lambda p: self._agent_priorities.get(p.agent_id, 0), reverse=True)
            winner = sorted_proposals[0]
            case.resolved_value = winner.proposed_value
            self._log_resolution(case_id, strategy, winner.agent_id, f"Priority resolution: {winner.agent_id}")

        elif strategy == ResolutionStrategy.VOTE:
            value_votes: Dict[str, float] = {}
            for p in case.proposals:
                key = str(p.proposed_value)
                value_votes[key] = value_votes.get(key, 0.0) + p.confidence
            winner_value = max(value_votes, key=value_votes.get)
            case.resolved_value = winner_value
            self._log_resolution(case_id, strategy, "consensus", f"Vote won with confidence {value_votes[winner_value]:.2f}")

        elif strategy == ResolutionStrategy.MERGE:
            merged = {}
            for p in case.proposals:
                if isinstance(p.proposed_value, dict):
                    for k, v in p.proposed_value.items():
                        if k not in merged:
                            merged[k] = v
            case.resolved_value = merged or case.proposals[0].proposed_value
            self._log_resolution(case_id, strategy, "merger", f"Merged {len(merged)} fields")

        elif strategy == ResolutionStrategy.ROLLBACK:
            case.resolved_value = None
            case.status = ResolutionStatus.ESCALATED
            self._log_resolution(case_id, strategy, "system", "Rolled back to last consistent state")

        elif strategy == ResolutionStrategy.DEFER:
            case.status = ResolutionStatus.DEFERRED
            self._log_resolution(case_id, strategy, "human", "Deferred to operator review")
            return case

        case.status = ResolutionStatus.RESOLVED
        case.resolved_at = time.time()
        self._total_resolved += 1
        return case

    def _log_resolution(self, case_id: str, strategy: ResolutionStrategy, winner: str, explanation: str):
        log = ResolutionLog(case_id=case_id, strategy=strategy, winner_agent=winner, explanation=explanation)
        self._resolution_log.append(log)
        if len(self._resolution_log) > 100:
            self._resolution_log = self._resolution_log[-100:]

    def get_active_conflicts(self) -> List[ConflictCase]:
        return [c for c in self._active_conflicts.values() if c.status not in (ResolutionStatus.RESOLVED, ResolutionStatus.ESCALATED)]

    def get_resolution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [{
            "log_id": l.log_id,
            "case_id": l.case_id,
            "strategy": l.strategy.value,
            "winner": l.winner_agent,
            "explanation": l.explanation,
        } for l in self._resolution_log[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_conflicts": len(self.get_active_conflicts()),
            "total_resolved": self._total_resolved,
            "deferred_count": sum(1 for c in self._active_conflicts.values() if c.status == ResolutionStatus.DEFERRED),
            "agent_priorities": dict(self._agent_priorities),
        }


def get_conflict_resolver() -> ConflictResolutionEngine:
    return ConflictResolutionEngine.get_instance()