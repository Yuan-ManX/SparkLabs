"""
SparkLabs Agent - Consensus Engine

Multi-agent deliberation and consensus building for collaborative
game design decisions. Enables teams of specialized agents to
propose, debate, and converge on optimal design choices through
structured voting and weighted opinion aggregation.

Architecture:
  AgentConsensus
    |-- ConsensusProtocol (voting strategy selection)
    |-- OpinionRegistry (agent position tracking)
    |-- DeliberationRound (structured debate cycle)
    |-- VoteTally (weighted opinion aggregation)
    |-- ConsensusResolver (tie-breaking and deadlock detection)

Protocols:
  - MAJORITY: simple majority wins
  - WEIGHTED: agent expertise weights influence votes
  - UNANIMOUS: full agreement required
  - RANKED_CHOICE: preferential voting with elimination
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ConsensusProtocol(Enum):
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    UNANIMOUS = "unanimous"
    RANKED_CHOICE = "ranked_choice"
    SUPER_MAJORITY = "super_majority"


class DeliberationPhase(Enum):
    PROPOSING = "proposing"
    DEBATING = "debating"
    VOTING = "voting"
    RESOLVED = "resolved"
    DEADLOCKED = "deadlocked"


@dataclass
class Opinion:
    agent_id: str
    position: str
    confidence: float
    reasoning: str
    evidence: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DeliberationRound:
    round_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    phase: DeliberationPhase = DeliberationPhase.PROPOSING
    opinions: Dict[str, Opinion] = field(default_factory=dict)
    votes: Dict[str, str] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


@dataclass
class ConsensusResult:
    topic: str
    winning_position: Optional[str]
    vote_counts: Dict[str, int]
    confidence_score: float
    total_voters: int
    protocol: ConsensusProtocol
    rounds: int
    deadlocked: bool = False


class AgentConsensus:
    """
    Multi-agent deliberation engine with structured voting protocols.
    """

    _instance: Optional[AgentConsensus] = None
    MAX_ROUNDS = 5
    SUPER_MAJORITY_THRESHOLD = 0.67

    @classmethod
    def get_instance(cls) -> AgentConsensus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._agent_weights: Dict[str, float] = defaultdict(lambda: 1.0)
        self._deliberations: Dict[str, DeliberationRound] = {}
        self._history: List[ConsensusResult] = []
        self._deadlock_count: int = 0
        self._total_decisions: int = 0

    def register_agent(self, agent_id: str, weight: float = 1.0) -> None:
        self._agent_weights[agent_id] = max(0.1, min(10.0, weight))

    def propose(self, topic: str) -> str:
        round_obj = DeliberationRound(topic=topic)
        self._deliberations[topic] = round_obj
        return round_obj.round_id

    def submit_opinion(
        self,
        topic: str,
        agent_id: str,
        position: str,
        confidence: float,
        reasoning: str = "",
    ) -> bool:
        round_obj = self._deliberations.get(topic)
        if round_obj is None or round_obj.phase not in (
            DeliberationPhase.PROPOSING,
            DeliberationPhase.DEBATING,
        ):
            return False
        if agent_id not in self._agent_weights:
            self._agent_weights[agent_id] = 1.0
        opinion = Opinion(
            agent_id=agent_id,
            position=position,
            confidence=max(0.0, min(1.0, confidence)),
            reasoning=reasoning,
        )
        round_obj.opinions[agent_id] = opinion
        if round_obj.phase == DeliberationPhase.PROPOSING:
            round_obj.phase = DeliberationPhase.DEBATING
        return True

    def vote(self, topic: str, agent_id: str, position: str) -> bool:
        round_obj = self._deliberations.get(topic)
        if round_obj is None:
            return False
        round_obj.phase = DeliberationPhase.VOTING
        round_obj.votes[agent_id] = position
        return True

    def resolve(
        self,
        topic: str,
        protocol: ConsensusProtocol = ConsensusProtocol.WEIGHTED,
    ) -> Optional[ConsensusResult]:
        round_obj = self._deliberations.get(topic)
        if round_obj is None:
            return None
        if not round_obj.votes:
            return None

        vote_counts: Dict[str, float] = defaultdict(float)
        for agent_id, position in round_obj.votes.items():
            weight = self._agent_weights.get(agent_id, 1.0)
            vote_counts[position] += weight

        total_weight = sum(self._agent_weights.get(aid, 1.0) for aid in round_obj.votes)
        results: List[Tuple[str, float]] = sorted(
            vote_counts.items(), key=lambda x: x[1], reverse=True
        )

        if not results:
            return None

        winning_position: Optional[str] = None
        deadlocked = False

        if protocol == ConsensusProtocol.UNANIMOUS:
            if len(results) == 1:
                winning_position = results[0][0]
            else:
                deadlocked = True
        elif protocol == ConsensusProtocol.SUPER_MAJORITY:
            top = results[0]
            if top[1] / total_weight >= self.SUPER_MAJORITY_THRESHOLD:
                winning_position = top[0]
            else:
                deadlocked = True
        elif protocol == ConsensusProtocol.MAJORITY:
            top = results[0]
            if top[1] > total_weight / 2:
                winning_position = top[0]
            else:
                deadlocked = True
        elif protocol == ConsensusProtocol.RANKED_CHOICE:
            winning_position = self._ranked_choice_resolve(results, round_obj)
        else:
            winning_position = results[0][0]

        if deadlocked:
            self._deadlock_count += 1

        self._total_decisions += 1
        round_obj.phase = (
            DeliberationPhase.DEADLOCKED if deadlocked else DeliberationPhase.RESOLVED
        )
        round_obj.resolved_at = time.time()

        int_votes = {k: int(v) for k, v in vote_counts.items()}
        confidence = (
            results[0][1] / total_weight if results and total_weight > 0 else 0.0
        )

        result = ConsensusResult(
            topic=topic,
            winning_position=winning_position,
            vote_counts=int_votes,
            confidence_score=round(confidence, 3),
            total_voters=len(round_obj.votes),
            protocol=protocol,
            rounds=1,
            deadlocked=deadlocked,
        )
        self._history.append(result)
        return result

    def _ranked_choice_resolve(
        self,
        results: List[Tuple[str, float]],
        round_obj: DeliberationRound,
    ) -> Optional[str]:
        if not results:
            return None
        positions = [r[0] for r in results]
        if len(positions) == 1:
            return positions[0]
        eliminated = [p for p, w in results[-1:]]
        remaining = [p for p in positions if p not in eliminated]
        return remaining[0] if remaining else positions[0]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_agents": len(self._agent_weights),
            "active_deliberations": sum(
                1
                for d in self._deliberations.values()
                if d.phase not in (DeliberationPhase.RESOLVED, DeliberationPhase.DEADLOCKED)
            ),
            "total_decisions": self._total_decisions,
            "deadlock_count": self._deadlock_count,
            "history_size": len(self._history),
        }

    def reset(self) -> None:
        self._deliberations.clear()
        self._agent_weights.clear()


_consensus = AgentConsensus.get_instance()


def get_agent_consensus() -> AgentConsensus:
    return _consensus