"""
SparkLabs Agent - Swarm Intelligence Engine

Collective intelligence fabric where autonomous agents converge,
share discoveries, and synthesize solutions through distributed
cognition. The engine orchestrates emergent swarm behavior across
the game creation pipeline, enabling agents to self-organize around
problems, build consensus, and amplify individual capabilities
through shared knowledge and coordinated action.

Architecture:
  SwarmIntelligenceEngine (singleton)
    |-- SwarmAgent (autonomous participant with identity and reputation)
    |-- ConsensusCompiler (Raft-inspired collective decision making)
    |-- TaskDisperser (capability-aware work distribution)
    |-- InsightReservoir (versioned, decaying shared knowledge)
    |-- PatternOracle (emergent behavior detection and serendipity logging)

Knowledge Flow:
  Agent observes → contributes to InsightReservoir → TaskDisperser
  matches work → SwarmAgent executes → ConsensusCompiler resolves
  disagreements → PatternOracle detects novelties → feedback loop
  refines agent reputations and knowledge confidence.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentDisposition(Enum):
    """Operational state of an agent within the swarm."""
    AVAILABLE = "available"
    BUSY = "busy"
    RESTING = "resting"
    OFFLINE = "offline"
    DETACHED = "detached"


class VoteProtocol(Enum):
    """Strategies for collective opinion aggregation."""
    PLAIN_MAJORITY = "plain_majority"
    TRUST_WEIGHTED = "trust_weighted"
    PREFERENCE_RANKED = "preference_ranked"
    QUORUM_THRESHOLD = "quorum_threshold"
    SUPER_MAJORITY = "super_majority"
    RAFT_TERM = "raft_term"


class ConsensusPhase(Enum):
    """Lifecycle stages of a consensus round."""
    NOMINATING = "nominating"
    CAMPAIGNING = "campaigning"
    BALLOTING = "balloting"
    TALLYING = "tallying"
    COMMITTED = "committed"
    STALEMATED = "stalemated"
    ABORTED = "aborted"


class TaskUrgency(Enum):
    """Priority tiers for work scheduling."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEFERRED = "deferred"


class TaskOutcome(Enum):
    """Terminal states for dispatched work units."""
    QUEUED = "queued"
    MATCHED = "matched"
    IN_FLIGHT = "in_flight"
    ACCOMPLISHED = "accomplished"
    FAULTED = "faulted"
    REASSIGNED = "reassigned"
    ABANDONED = "abandoned"


class KnowledgeCategory(Enum):
    """Taxonomy of shared knowledge entries."""
    OBSERVATION = "observation"
    INFERENCE = "inference"
    BLUEPRINT = "blueprint"
    CAUTION = "caution"
    HEURISTIC = "heuristic"
    DISCOVERY = "discovery"


class EmergenceSignal(Enum):
    """Types of emergent behavior detected by the oracle."""
    NOVEL_STRATEGY = "novel_strategy"
    COLLECTIVE_RHYTHM = "collective_rhythm"
    SYNERGY_BURST = "synergy_burst"
    ROLE_SHIFT = "role_shift"
    IMPROVISED_COORDINATION = "improvised_coordination"
    SERENDIPITOUS_FIND = "serendipitous_find"
    PHASE_TRANSITION = "phase_transition"
    UNEXPECTED_CONSENSUS = "unexpected_consensus"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SwarmAgent:
    """Autonomous participant carrying identity, capabilities, and reputation.

    Each agent maintains a private knowledge cache, a communication inbox,
    and a reputation score that evolves based on swarm contributions.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    moniker: str = ""
    capabilities: List[str] = field(default_factory=list)
    disposition: AgentDisposition = AgentDisposition.AVAILABLE
    current_task_id: Optional[str] = None
    capacity: int = 5
    active_load: int = 0
    reputation: float = 1.0
    total_contributions: int = 0
    successful_contributions: int = 0
    knowledge_cache: List[str] = field(default_factory=list)
    inbox: List[Dict[str, Any]] = field(default_factory=list)
    registered_at: float = field(default_factory=_time_module.time)
    last_heartbeat: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.disposition == AgentDisposition.AVAILABLE and self.active_load < self.capacity

    @property
    def success_rate(self) -> float:
        if self.total_contributions == 0:
            return 1.0
        return self.successful_contributions / self.total_contributions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "moniker": self.moniker,
            "capabilities": list(self.capabilities),
            "disposition": self.disposition.value,
            "current_task_id": self.current_task_id,
            "capacity": self.capacity,
            "active_load": self.active_load,
            "reputation": self.reputation,
            "total_contributions": self.total_contributions,
            "successful_contributions": self.successful_contributions,
            "success_rate": self.success_rate,
            "is_available": self.is_available,
            "knowledge_cache_size": len(self.knowledge_cache),
            "inbox_size": len(self.inbox),
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "metadata": dict(self.metadata),
        }


@dataclass
class SwarmTasklet:
    """A unit of work dispatched through the swarm.

    Carries capability requirements, dependency chains, and a
    confidence score that grows as the swarm validates the result.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    title: str = ""
    description: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    urgency: TaskUrgency = TaskUrgency.MEDIUM
    outcome: TaskOutcome = TaskOutcome.QUEUED
    assigned_agent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: float = field(default_factory=_time_module.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    reassignment_history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "title": self.title,
            "description": self.description,
            "required_capabilities": list(self.required_capabilities),
            "urgency": self.urgency.value,
            "outcome": self.outcome.value,
            "assigned_agent_id": self.assigned_agent_id,
            "dependencies": list(self.dependencies),
            "result": self.result,
            "confidence": self.confidence,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "reassignment_history": list(self.reassignment_history),
            "metadata": dict(self.metadata),
        }


@dataclass
class ConsensusBallot:
    """A single proposal within a consensus round, carrying votes and
    Raft-inspired term tracking for distributed agreement.
    """

    ballot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    topic: str = ""
    description: str = ""
    options: List[str] = field(default_factory=list)
    phase: ConsensusPhase = ConsensusPhase.NOMINATING
    protocol: VoteProtocol = VoteProtocol.TRUST_WEIGHTED
    term: int = 0
    leader_id: Optional[str] = None
    votes: Dict[str, str] = field(default_factory=dict)
    vote_weights: Dict[str, float] = field(default_factory=dict)
    winning_option: Optional[str] = None
    confidence: float = 0.0
    round_count: int = 0
    max_rounds: int = 5
    deadlocked: bool = False
    opened_at: float = field(default_factory=_time_module.time)
    committed_at: Optional[float] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ballot_id": self.ballot_id,
            "topic": self.topic,
            "description": self.description,
            "options": list(self.options),
            "phase": self.phase.value,
            "protocol": self.protocol.value,
            "term": self.term,
            "leader_id": self.leader_id,
            "votes": dict(self.votes),
            "vote_weights": dict(self.vote_weights),
            "winning_option": self.winning_option,
            "confidence": self.confidence,
            "round_count": self.round_count,
            "max_rounds": self.max_rounds,
            "deadlocked": self.deadlocked,
            "opened_at": self.opened_at,
            "committed_at": self.committed_at,
            "history": list(self.history),
        }


@dataclass
class KnowledgeGranule:
    """A discrete unit of shared knowledge with versioning and decay.

    Knowledge confidence decays over time unless refreshed by
    corroborating observations from other agents.
    """

    granule_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    key: str = ""
    value: Any = None
    category: KnowledgeCategory = KnowledgeCategory.OBSERVATION
    contributor_id: str = ""
    confidence: float = 1.0
    version: int = 1
    corroborations: int = 0
    conflicts: int = 0
    decay_rate: float = 0.01
    refresh_interval: float = 3600.0
    created_at: float = field(default_factory=_time_module.time)
    refreshed_at: float = field(default_factory=_time_module.time)
    ttl: float = 0.0
    tags: List[str] = field(default_factory=list)
    predecessor_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def effective_confidence(self) -> float:
        elapsed = _time_module.time() - self.refreshed_at
        if self.ttl > 0.0 and elapsed > self.ttl:
            return 0.0
        decay = max(0.0, 1.0 - elapsed * self.decay_rate / self.refresh_interval)
        corroboration_bonus = min(0.3, self.corroborations * 0.05)
        conflict_penalty = min(0.5, self.conflicts * 0.1)
        return max(0.0, min(1.0, self.confidence * decay + corroboration_bonus - conflict_penalty))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "granule_id": self.granule_id,
            "key": self.key,
            "value": self.value,
            "category": self.category.value,
            "contributor_id": self.contributor_id,
            "confidence": self.confidence,
            "effective_confidence": self.effective_confidence,
            "version": self.version,
            "corroborations": self.corroborations,
            "conflicts": self.conflicts,
            "decay_rate": self.decay_rate,
            "refresh_interval": self.refresh_interval,
            "created_at": self.created_at,
            "refreshed_at": self.refreshed_at,
            "ttl": self.ttl,
            "tags": list(self.tags),
            "predecessor_id": self.predecessor_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class EmergenceTrace:
    """A recorded instance of emergent behavior detected by the oracle.

    Captures the agents involved, the pattern recognized, and a
    narrative describing the serendipitous discovery.
    """

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    signal: EmergenceSignal = EmergenceSignal.NOVEL_STRATEGY
    agents_involved: List[str] = field(default_factory=list)
    pattern_signature: str = ""
    narrative: str = ""
    significance: float = 0.5
    observed_at: float = field(default_factory=_time_module.time)
    context: Dict[str, Any] = field(default_factory=dict)
    related_traces: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "signal": self.signal.value,
            "agents_involved": list(self.agents_involved),
            "pattern_signature": self.pattern_signature,
            "narrative": self.narrative,
            "significance": self.significance,
            "observed_at": self.observed_at,
            "context": dict(self.context),
            "related_traces": list(self.related_traces),
        }


# ---------------------------------------------------------------------------
# ConsensusCompiler
# ---------------------------------------------------------------------------


class ConsensusCompiler:
    """Collective decision-making engine with Raft-inspired agreement.

    Drives structured consensus rounds where agents nominate options,
    campaign for their positions, cast weighted ballots, and converge
    on a committed decision. Supports stalemate breaking through
    round-limited escalation and forced resolution.
    """

    def __init__(self) -> None:
        self._ballots: Dict[str, ConsensusBallot] = {}
        self._term_counter: int = 0
        self._history: Deque[Dict[str, Any]] = deque(maxlen=500)
        self._stalemate_count: int = 0
        self._total_resolutions: int = 0

    def initiate_ballot(
        self,
        topic: str,
        description: str,
        options: List[str],
        protocol: VoteProtocol = VoteProtocol.TRUST_WEIGHTED,
        max_rounds: int = 5,
        leader_id: Optional[str] = None,
    ) -> ConsensusBallot:
        self._term_counter += 1
        ballot = ConsensusBallot(
            topic=topic,
            description=description,
            options=list(options),
            protocol=protocol,
            term=self._term_counter,
            leader_id=leader_id,
            max_rounds=max_rounds,
            phase=ConsensusPhase.NOMINATING,
        )
        self._ballots[ballot.ballot_id] = ballot
        return ballot

    def register_nomination(
        self,
        ballot_id: str,
        option: str,
    ) -> bool:
        ballot = self._ballots.get(ballot_id)
        if ballot is None:
            return False
        if ballot.phase not in (ConsensusPhase.NOMINATING, ConsensusPhase.CAMPAIGNING):
            return False
        if option not in ballot.options:
            ballot.options.append(option)
        ballot.phase = ConsensusPhase.CAMPAIGNING
        return True

    def cast_vote(
        self,
        ballot_id: str,
        voter_id: str,
        option: str,
        weight: float = 1.0,
    ) -> bool:
        ballot = self._ballots.get(ballot_id)
        if ballot is None:
            return False
        if ballot.phase not in (ConsensusPhase.CAMPAIGNING, ConsensusPhase.BALLOTING):
            return False
        if option not in ballot.options:
            return False
        ballot.phase = ConsensusPhase.BALLOTING
        ballot.votes[voter_id] = option
        ballot.vote_weights[voter_id] = max(0.1, weight)
        return True

    def tally(self, ballot_id: str) -> Optional[ConsensusBallot]:
        """Execute one round of vote tallying with the ballot's protocol.

        Returns the ballot with updated phase, winning_option, and
        confidence. Stalemates are detected when no option meets the
        protocol's threshold.
        """
        ballot = self._ballots.get(ballot_id)
        if ballot is None:
            return None
        if ballot.phase not in (ConsensusPhase.BALLOTING, ConsensusPhase.TALLYING):
            return None

        ballot.phase = ConsensusPhase.TALLYING
        ballot.round_count += 1

        if not ballot.votes:
            ballot.phase = ConsensusPhase.STALEMATED
            ballot.deadlocked = True
            self._stalemate_count += 1
            self._history.append({
                "event": "stalemate",
                "ballot_id": ballot_id,
                "topic": ballot.topic,
                "round": ballot.round_count,
                "timestamp": _time_module.time(),
            })
            return ballot

        tally: Dict[str, float] = defaultdict(float)
        for voter_id, option in ballot.votes.items():
            w = ballot.vote_weights.get(voter_id, 1.0)
            tally[option] += w

        total_weight = sum(tally.values())
        ranked = sorted(tally.items(), key=lambda x: x[1], reverse=True)

        if not ranked:
            ballot.phase = ConsensusPhase.STALEMATED
            ballot.deadlocked = True
            self._stalemate_count += 1
            return ballot

        winner: Optional[str] = None
        protocol = ballot.protocol

        if protocol == VoteProtocol.PLAIN_MAJORITY:
            if ranked[0][1] > total_weight / 2.0:
                winner = ranked[0][0]
        elif protocol == VoteProtocol.TRUST_WEIGHTED:
            winner = ranked[0][0]
        elif protocol == VoteProtocol.PREFERENCE_RANKED:
            winner = self._resolve_preference_ranked(ranked, ballot)
        elif protocol == VoteProtocol.QUORUM_THRESHOLD:
            if len(ballot.votes) >= 3 and ranked[0][1] > total_weight / 2.0:
                winner = ranked[0][0]
        elif protocol == VoteProtocol.SUPER_MAJORITY:
            if ranked[0][1] / total_weight >= 0.67:
                winner = ranked[0][0]
        elif protocol == VoteProtocol.RAFT_TERM:
            if ballot.leader_id and ballot.leader_id in ballot.votes:
                leader_vote = ballot.votes[ballot.leader_id]
                if leader_vote in tally:
                    if tally[leader_vote] > total_weight / 2.0:
                        winner = leader_vote
            if winner is None:
                winner = ranked[0][0]

        if winner is not None:
            ballot.winning_option = winner
            ballot.confidence = ranked[0][1] / total_weight if total_weight > 0 else 0.0
            ballot.phase = ConsensusPhase.COMMITTED
            ballot.committed_at = _time_module.time()
            ballot.deadlocked = False
            self._total_resolutions += 1
            self._history.append({
                "event": "committed",
                "ballot_id": ballot_id,
                "topic": ballot.topic,
                "winner": winner,
                "confidence": ballot.confidence,
                "round": ballot.round_count,
                "timestamp": _time_module.time(),
            })
        else:
            if ballot.round_count >= ballot.max_rounds:
                ballot.phase = ConsensusPhase.STALEMATED
                ballot.deadlocked = True
                ballot.winning_option = ranked[0][0] if ranked else None
                ballot.confidence = ranked[0][1] / total_weight if ranked and total_weight > 0 else 0.0
                self._stalemate_count += 1
                self._history.append({
                    "event": "stalemate_exhausted",
                    "ballot_id": ballot_id,
                    "topic": ballot.topic,
                    "round": ballot.round_count,
                    "timestamp": _time_module.time(),
                })
            else:
                ballot.phase = ConsensusPhase.CAMPAIGNING

        ballot.history.append({
            "round": ballot.round_count,
            "phase": ballot.phase.value,
            "tally": dict(tally),
            "winner": ballot.winning_option,
            "timestamp": _time_module.time(),
        })

        return ballot

    def break_stalemate(self, ballot_id: str, tiebreaker: str = "highest_confidence") -> Optional[ConsensusBallot]:
        """Force resolution of a deadlocked ballot.

        Strategies:
          - highest_confidence: select the option with the most confident voters.
          - random_choice: pick uniformly from the leading options.
          - leader_decree: the term leader's preference wins.
        """
        ballot = self._ballots.get(ballot_id)
        if ballot is None or not ballot.deadlocked:
            return None

        ranked: Dict[str, float] = defaultdict(float)
        for voter_id, option in ballot.votes.items():
            w = ballot.vote_weights.get(voter_id, 1.0)
            ranked[option] += w

        sorted_options = sorted(ranked.items(), key=lambda x: x[1], reverse=True)
        if not sorted_options:
            return ballot

        if tiebreaker == "leader_decree" and ballot.leader_id and ballot.leader_id in ballot.votes:
            ballot.winning_option = ballot.votes[ballot.leader_id]
        elif tiebreaker == "random_choice":
            import random
            top_weight = sorted_options[0][1]
            contenders = [opt for opt, w in sorted_options if w >= top_weight * 0.9]
            ballot.winning_option = random.choice(contenders)
        else:
            ballot.winning_option = sorted_options[0][0]

        total_weight = sum(ranked.values())
        ballot.confidence = ranked[ballot.winning_option] / total_weight if total_weight > 0 else 0.5
        ballot.phase = ConsensusPhase.COMMITTED
        ballot.committed_at = _time_module.time()
        ballot.deadlocked = False
        self._total_resolutions += 1

        self._history.append({
            "event": "stalemate_broken",
            "ballot_id": ballot_id,
            "topic": ballot.topic,
            "winner": ballot.winning_option,
            "tiebreaker": tiebreaker,
            "timestamp": _time_module.time(),
        })

        return ballot

    def _resolve_preference_ranked(
        self,
        ranked: List[Tuple[str, float]],
        ballot: ConsensusBallot,
    ) -> Optional[str]:
        """Iterative elimination for ranked-choice voting.

        Eliminates the lowest-ranked option each round, redistributing
        votes to the next preference until a majority emerges.
        """
        if not ranked:
            return None
        if len(ranked) == 1:
            return ranked[0][0]

        total_weight = sum(w for _, w in ranked)
        if ranked[0][1] > total_weight / 2.0:
            return ranked[0][0]

        eliminated = ranked[-1][0]
        remaining_options = [opt for opt in ballot.options if opt != eliminated]
        recount: Dict[str, float] = defaultdict(float)
        for voter_id, option in ballot.votes.items():
            if option == eliminated:
                continue
            if option in remaining_options:
                w = ballot.vote_weights.get(voter_id, 1.0)
                recount[option] += w

        new_ranked = sorted(recount.items(), key=lambda x: x[1], reverse=True)
        if new_ranked:
            new_total = sum(w for _, w in new_ranked)
            if new_ranked[0][1] > new_total / 2.0:
                return new_ranked[0][0]
            return new_ranked[0][0]
        return ranked[0][0]

    def get_ballot(self, ballot_id: str) -> Optional[Dict[str, Any]]:
        ballot = self._ballots.get(ballot_id)
        return ballot.to_dict() if ballot else None

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for b in self._ballots.values() if b.phase not in (
            ConsensusPhase.COMMITTED, ConsensusPhase.STALEMATED, ConsensusPhase.ABORTED,
        ))
        return {
            "active_ballots": active,
            "total_ballots": len(self._ballots),
            "total_resolutions": self._total_resolutions,
            "stalemate_count": self._stalemate_count,
            "current_term": self._term_counter,
            "history_size": len(self._history),
        }

    def reset(self) -> None:
        self._ballots.clear()
        self._history.clear()
        self._term_counter = 0
        self._stalemate_count = 0
        self._total_resolutions = 0


# ---------------------------------------------------------------------------
# TaskDisperser
# ---------------------------------------------------------------------------


class TaskDisperser:
    """Capability-aware work distributor with load balancing.

    Matches incoming tasklets to the most suitable agents based on
    capability overlap, current load, and historical success rates.
    Manages dependency chains and reassigns faulted tasks to
    alternate agents.
    """

    def __init__(self) -> None:
        self._tasklets: Dict[str, SwarmTasklet] = {}
        self._queue: Deque[str] = deque()
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        self._dispatched_count: int = 0
        self._accomplished_count: int = 0
        self._faulted_count: int = 0
        self._reassigned_count: int = 0

    def submit_tasklet(
        self,
        title: str,
        description: str,
        required_capabilities: Optional[List[str]] = None,
        urgency: TaskUrgency = TaskUrgency.MEDIUM,
        dependencies: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        max_attempts: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwarmTasklet:
        tasklet = SwarmTasklet(
            parent_id=parent_id,
            title=title,
            description=description,
            required_capabilities=required_capabilities or [],
            urgency=urgency,
            outcome=TaskOutcome.QUEUED,
            dependencies=dependencies or [],
            max_attempts=max_attempts,
            metadata=metadata or {},
        )
        self._tasklets[tasklet.id] = tasklet
        self._queue.append(tasklet.id)

        for dep_id in tasklet.dependencies:
            self._dependency_graph[dep_id].add(tasklet.id)
            self._reverse_deps[tasklet.id].add(dep_id)

        return tasklet

    def match_to_agent(
        self,
        tasklet_id: str,
        agents: Dict[str, SwarmAgent],
    ) -> Optional[str]:
        """Find the best available agent for a tasklet.

        Scoring weights: capability overlap (40%), current load
        inverse (25%), reputation (20%), historical fit (15%).
        """
        tasklet = self._tasklets.get(tasklet_id)
        if tasklet is None:
            return None
        if tasklet.outcome != TaskOutcome.QUEUED:
            return None

        for dep_id in tasklet.dependencies:
            dep = self._tasklets.get(dep_id)
            if dep is None or dep.outcome != TaskOutcome.ACCOMPLISHED:
                return None

        candidates = [a for a in agents.values() if a.is_available]
        if not candidates:
            return None

        scored: List[Tuple[SwarmAgent, float]] = []
        for agent in candidates:
            score = 0.0

            cap_overlap = len(set(tasklet.required_capabilities) & set(agent.capabilities))
            if tasklet.required_capabilities:
                cap_ratio = cap_overlap / len(tasklet.required_capabilities)
            else:
                cap_ratio = 1.0
            score += cap_ratio * 40.0

            load_ratio = 1.0 - (agent.active_load / max(1, agent.capacity))
            score += load_ratio * 25.0

            score += agent.reputation * 20.0

            score += agent.success_rate * 15.0

            if agent.id in tasklet.reassignment_history:
                score -= 10.0

            scored.append((agent, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0].id if scored else None

    def dispatch(self, tasklet_id: str, agent_id: str) -> bool:
        tasklet = self._tasklets.get(tasklet_id)
        if tasklet is None:
            return False
        if tasklet.outcome != TaskOutcome.QUEUED:
            return False

        tasklet.assigned_agent_id = agent_id
        tasklet.outcome = TaskOutcome.MATCHED
        tasklet.started_at = _time_module.time()

        if tasklet_id in self._queue:
            self._queue.remove(tasklet_id)

        self._dispatched_count += 1
        return True

    def mark_accomplished(
        self,
        tasklet_id: str,
        result: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> bool:
        tasklet = self._tasklets.get(tasklet_id)
        if tasklet is None:
            return False
        if tasklet.outcome not in (TaskOutcome.MATCHED, TaskOutcome.IN_FLIGHT):
            return False

        tasklet.outcome = TaskOutcome.ACCOMPLISHED
        tasklet.result = result or {}
        tasklet.confidence = confidence
        tasklet.completed_at = _time_module.time()
        if tasklet.started_at:
            tasklet.duration_ms = (tasklet.completed_at - tasklet.started_at) * 1000.0
        self._accomplished_count += 1
        return True

    def mark_faulted(self, tasklet_id: str) -> bool:
        tasklet = self._tasklets.get(tasklet_id)
        if tasklet is None:
            return False
        if tasklet.outcome not in (TaskOutcome.MATCHED, TaskOutcome.IN_FLIGHT):
            return False

        tasklet.attempt_count += 1
        if tasklet.attempt_count >= tasklet.max_attempts:
            tasklet.outcome = TaskOutcome.FAULTED
            tasklet.completed_at = _time_module.time()
            self._faulted_count += 1
        else:
            tasklet.outcome = TaskOutcome.REASSIGNED
            tasklet.reassignment_history.append(tasklet.assigned_agent_id or "unknown")
            tasklet.assigned_agent_id = None
            self._queue.appendleft(tasklet_id)
            self._reassigned_count += 1
        return True

    def get_ready_tasklets(self) -> List[SwarmTasklet]:
        """Return queued tasklets whose dependencies are all satisfied."""
        ready: List[SwarmTasklet] = []
        priority_order = {
            TaskUrgency.CRITICAL: 0,
            TaskUrgency.HIGH: 1,
            TaskUrgency.MEDIUM: 2,
            TaskUrgency.LOW: 3,
            TaskUrgency.DEFERRED: 4,
        }
        for tid in list(self._queue):
            tasklet = self._tasklets.get(tid)
            if tasklet is None or tasklet.outcome != TaskOutcome.QUEUED:
                continue
            deps_ready = all(
                self._tasklets.get(d) is not None and self._tasklets[d].outcome == TaskOutcome.ACCOMPLISHED
                for d in tasklet.dependencies
            )
            if deps_ready:
                ready.append(tasklet)
        ready.sort(key=lambda t: (priority_order.get(t.urgency, 2), t.created_at))
        return ready

    def get_tasklet(self, tasklet_id: str) -> Optional[Dict[str, Any]]:
        tasklet = self._tasklets.get(tasklet_id)
        return tasklet.to_dict() if tasklet else None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_tasklets": len(self._tasklets),
            "queued": sum(1 for t in self._tasklets.values() if t.outcome == TaskOutcome.QUEUED),
            "matched": sum(1 for t in self._tasklets.values() if t.outcome == TaskOutcome.MATCHED),
            "in_flight": sum(1 for t in self._tasklets.values() if t.outcome == TaskOutcome.IN_FLIGHT),
            "accomplished": self._accomplished_count,
            "faulted": self._faulted_count,
            "reassigned": self._reassigned_count,
            "dispatched": self._dispatched_count,
        }

    def reset(self) -> None:
        self._tasklets.clear()
        self._queue.clear()
        self._dependency_graph.clear()
        self._reverse_deps.clear()
        self._dispatched_count = 0
        self._accomplished_count = 0
        self._faulted_count = 0
        self._reassigned_count = 0


# ---------------------------------------------------------------------------
# InsightReservoir
# ---------------------------------------------------------------------------


class InsightReservoir:
    """Versioned, decaying shared knowledge repository.

    Agents contribute observations, inferences, and discoveries.
    Knowledge confidence naturally decays over time unless refreshed
    by corroborating contributions. Conflicting entries are detected
    and resolved through confidence-weighted arbitration.
    """

    def __init__(self, max_granules: int = 1000) -> None:
        self._granules: Dict[str, KnowledgeGranule] = {}
        self._key_index: Dict[str, str] = {}
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._contributor_index: Dict[str, Set[str]] = defaultdict(set)
        self._max_granules = max_granules
        self._version_counter: Dict[str, int] = defaultdict(int)
        self._access_log: Deque[Dict[str, Any]] = deque(maxlen=500)

    def contribute(
        self,
        key: str,
        value: Any,
        contributor_id: str,
        category: KnowledgeCategory = KnowledgeCategory.OBSERVATION,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        ttl: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeGranule:
        tag_list = tags or []

        existing_id = self._key_index.get(key)
        if existing_id is not None and existing_id in self._granules:
            existing = self._granules[existing_id]
            if value == existing.value:
                existing.corroborations += 1
                existing.confidence = min(1.0, existing.confidence + 0.05)
                existing.refreshed_at = _time_module.time()
                return existing
            else:
                existing.conflicts += 1

                if confidence > existing.effective_confidence:
                    self._version_counter[key] += 1
                    granule = KnowledgeGranule(
                        key=key,
                        value=value,
                        category=category,
                        contributor_id=contributor_id,
                        confidence=confidence,
                        version=self._version_counter[key],
                        predecessor_id=existing.granule_id,
                        ttl=ttl,
                        tags=tag_list,
                        metadata=metadata or {},
                    )
                    self._evict_if_needed()
                    self._granules[granule.granule_id] = granule
                    self._key_index[key] = granule.granule_id
                    for tag in tag_list:
                        self._tag_index[tag].add(granule.granule_id)
                    self._contributor_index[contributor_id].add(granule.granule_id)
                    return granule
                else:
                    return existing

        self._version_counter[key] += 1
        granule = KnowledgeGranule(
            key=key,
            value=value,
            category=category,
            contributor_id=contributor_id,
            confidence=confidence,
            version=self._version_counter[key],
            ttl=ttl,
            tags=tag_list,
            metadata=metadata or {},
        )

        self._evict_if_needed()
        self._granules[granule.granule_id] = granule
        self._key_index[key] = granule.granule_id
        for tag in tag_list:
            self._tag_index[tag].add(granule.granule_id)
        self._contributor_index[contributor_id].add(granule.granule_id)

        return granule

    def retrieve(self, key: str) -> Optional[KnowledgeGranule]:
        granule_id = self._key_index.get(key)
        if granule_id is None:
            return None
        granule = self._granules.get(granule_id)
        if granule is None:
            return None

        if granule.effective_confidence <= 0.0:
            return None

        self._access_log.append({
            "key": key,
            "granule_id": granule.granule_id,
            "timestamp": _time_module.time(),
        })
        return granule

    def search(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
        category: Optional[KnowledgeCategory] = None,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> List[KnowledgeGranule]:
        results: List[KnowledgeGranule] = []
        query_lower = query.lower()

        for granule in self._granules.values():
            if granule.effective_confidence < min_confidence:
                continue

            if category is not None and granule.category != category:
                continue

            if tags is not None:
                if not set(tags).intersection(granule.tags):
                    continue

            if query_lower:
                key_match = query_lower in granule.key.lower()
                value_match = isinstance(granule.value, str) and query_lower in granule.value.lower()
                if not (key_match or value_match):
                    continue

            results.append(granule)

        results.sort(key=lambda g: g.effective_confidence * (1 + g.corroborations * 0.1), reverse=True)
        return results[:limit]

    def refresh(self, key: str) -> bool:
        granule_id = self._key_index.get(key)
        if granule_id is None:
            return False
        granule = self._granules.get(granule_id)
        if granule is None:
            return False
        granule.refreshed_at = _time_module.time()
        return True

    def get_version_history(self, key: str) -> List[Dict[str, Any]]:
        """Walk the predecessor chain to reconstruct version history."""
        granule_id = self._key_index.get(key)
        if granule_id is None:
            return []
        history: List[Dict[str, Any]] = []
        current_id = granule_id
        while current_id is not None:
            granule = self._granules.get(current_id)
            if granule is None:
                break
            history.append({
                "granule_id": granule.granule_id,
                "version": granule.version,
                "contributor_id": granule.contributor_id,
                "confidence": granule.confidence,
                "created_at": granule.created_at,
            })
            current_id = granule.predecessor_id
        return history

    def list_contributions(self, contributor_id: str) -> List[Dict[str, Any]]:
        granule_ids = self._contributor_index.get(contributor_id, set())
        return [self._granules[gid].to_dict() for gid in granule_ids if gid in self._granules]

    def _evict_if_needed(self) -> None:
        if len(self._granules) <= self._max_granules:
            return
        sorted_granules = sorted(
            self._granules.values(),
            key=lambda g: g.effective_confidence,
        )
        to_remove = len(self._granules) - self._max_granules
        for i in range(to_remove):
            g = sorted_granules[i]
            if self._key_index.get(g.key) == g.granule_id:
                del self._key_index[g.key]
            for tag in g.tags:
                tag_set = self._tag_index.get(tag)
                if tag_set:
                    tag_set.discard(g.granule_id)
            contrib_set = self._contributor_index.get(g.contributor_id)
            if contrib_set:
                contrib_set.discard(g.granule_id)
            del self._granules[g.granule_id]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_granules": len(self._granules),
            "max_granules": self._max_granules,
            "unique_keys": len(self._key_index),
            "unique_tags": len(self._tag_index),
            "unique_contributors": len(self._contributor_index),
            "avg_confidence": sum(g.effective_confidence for g in self._granules.values()) / max(1, len(self._granules)),
            "total_corroborations": sum(g.corroborations for g in self._granules.values()),
            "total_conflicts": sum(g.conflicts for g in self._granules.values()),
        }

    def reset(self) -> None:
        self._granules.clear()
        self._key_index.clear()
        self._tag_index.clear()
        self._contributor_index.clear()
        self._version_counter.clear()
        self._access_log.clear()


# ---------------------------------------------------------------------------
# PatternOracle
# ---------------------------------------------------------------------------


class PatternOracle:
    """Detects emergent behaviors and serendipitous discoveries.

    Monitors the swarm's collective activity stream for patterns
    that transcend individual agent actions. Identifies novel
    strategies, phase transitions, and unexpected coordination
    phenomena that signal emergent intelligence.
    """

    def __init__(self) -> None:
        self._traces: List[EmergenceTrace] = []
        self._activity_stream: Deque[Dict[str, Any]] = deque(maxlen=1000)
        self._agent_patterns: Dict[str, Deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=100))
        self._collective_signatures: Dict[str, int] = defaultdict(int)
        self._innovation_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._detection_threshold: float = 0.6

    def observe_action(
        self,
        agent_id: str,
        action_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "agent_id": agent_id,
            "action_type": action_type,
            "context": context or {},
            "timestamp": _time_module.time(),
        }
        self._activity_stream.append(record)
        self._agent_patterns[agent_id].append(record)

    def analyze(self) -> List[EmergenceTrace]:
        """Scan the activity stream for emergent patterns.

        Returns a list of newly detected emergence traces.
        """
        new_traces: List[EmergenceTrace] = []

        if len(self._activity_stream) < 5:
            return new_traces

        novel_trace = self._detect_novel_strategy()
        if novel_trace:
            new_traces.append(novel_trace)

        rhythm_trace = self._detect_collective_rhythm()
        if rhythm_trace:
            new_traces.append(rhythm_trace)

        synergy_trace = self._detect_synergy_burst()
        if synergy_trace:
            new_traces.append(synergy_trace)

        serendipity_trace = self._detect_serendipitous_find()
        if serendipity_trace:
            new_traces.append(serendipity_trace)

        for trace in new_traces:
            self._traces.append(trace)
            sig = trace.pattern_signature
            self._collective_signatures[sig] += 1
            self._innovation_log.append({
                "trace_id": trace.trace_id,
                "signal": trace.signal.value,
                "significance": trace.significance,
                "timestamp": trace.observed_at,
            })

        return new_traces

    def _detect_novel_strategy(self) -> Optional[EmergenceTrace]:
        recent = list(self._activity_stream)[-50:]
        if len(recent) < 10:
            return None

        action_types = [r["action_type"] for r in recent]
        unique_actions = set(action_types)
        if len(unique_actions) < 3:
            return None

        agents_involved = list(set(r["agent_id"] for r in recent))
        if len(agents_involved) < 3:
            return None

        action_freq: Dict[str, int] = defaultdict(int)
        for at in action_types:
            action_freq[at] += 1

        rare_actions = [at for at, count in action_freq.items() if count <= 2 and len(recent) > 10]
        if not rare_actions:
            return None

        significance = min(1.0, len(rare_actions) / 5.0)
        if significance < self._detection_threshold:
            return None

        return EmergenceTrace(
            signal=EmergenceSignal.NOVEL_STRATEGY,
            agents_involved=agents_involved,
            pattern_signature=f"novel:{'|'.join(sorted(rare_actions))}",
            narrative=f"Agents {', '.join(agents_involved[:3])} generated novel action patterns: {', '.join(rare_actions)}",
            significance=significance,
            context={"rare_actions": rare_actions, "total_actions": len(action_types)},
        )

    def _detect_collective_rhythm(self) -> Optional[EmergenceTrace]:
        agent_actions = self._agent_patterns
        if len(agent_actions) < 3:
            return None

        interleaved: Dict[str, int] = defaultdict(int)
        agent_ids = list(agent_actions.keys())
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                a_actions = agent_actions[agent_ids[i]]
                b_actions = agent_actions[agent_ids[j]]
                if len(a_actions) < 5 or len(b_actions) < 5:
                    continue
                a_times = [a["timestamp"] for a in a_actions]
                b_times = [b["timestamp"] for b in b_actions]
                interleavings = 0
                for at in a_times:
                    for bt in b_times:
                        if abs(at - bt) < 2.0:
                            interleavings += 1
                if interleavings >= 3:
                    pair_key = f"{min(agent_ids[i], agent_ids[j])}-{max(agent_ids[i], agent_ids[j])}"
                    interleaved[pair_key] = interleavings

        if not interleaved:
            return None

        top_pair = max(interleaved, key=lambda k: interleaved[k])
        a1, a2 = top_pair.split("-")
        significance = min(1.0, interleaved[top_pair] / 10.0)

        if significance < self._detection_threshold:
            return None

        return EmergenceTrace(
            signal=EmergenceSignal.COLLECTIVE_RHYTHM,
            agents_involved=[a1, a2],
            pattern_signature=f"rhythm:{top_pair}",
            narrative=f"Agents {a1} and {a2} exhibit synchronized action rhythm with {interleaved[top_pair]} interleavings",
            significance=significance,
            context={"interleavings": interleaved[top_pair]},
        )

    def _detect_synergy_burst(self) -> Optional[EmergenceTrace]:
        recent = list(self._activity_stream)[-30:]
        if len(recent) < 10:
            return None

        agent_bursts: Dict[str, int] = defaultdict(int)
        window_start = recent[0]["timestamp"]
        for r in recent:
            if r["timestamp"] - window_start < 5.0:
                agent_bursts[r["agent_id"]] += 1

        bursty_agents = [aid for aid, count in agent_bursts.items() if count >= 3]
        if len(bursty_agents) < 3:
            return None

        significance = min(1.0, len(bursty_agents) / 5.0)
        if significance < self._detection_threshold:
            return None

        return EmergenceTrace(
            signal=EmergenceSignal.SYNERGY_BURST,
            agents_involved=bursty_agents,
            pattern_signature=f"synergy:{'|'.join(sorted(bursty_agents))}",
            narrative=f"Synergy burst detected among {len(bursty_agents)} agents within a tight window",
            significance=significance,
            context={"bursty_agents": bursty_agents, "window_size": 5.0},
        )

    def _detect_serendipitous_find(self) -> Optional[EmergenceTrace]:
        recent = list(self._activity_stream)[-20:]
        if len(recent) < 8:
            return None

        context_keys: Dict[str, int] = defaultdict(int)
        for r in recent:
            ctx = r.get("context", {})
            for k in ctx:
                context_keys[k] += 1

        novel_keys = [k for k, count in context_keys.items() if count == 1 and len(recent) > 10]
        if not novel_keys:
            return None

        agents_involved = list(set(r["agent_id"] for r in recent if any(
            k in r.get("context", {}) for k in novel_keys
        )))

        if not agents_involved:
            return None

        significance = min(1.0, len(novel_keys) / 3.0)
        if significance < self._detection_threshold:
            return None

        return EmergenceTrace(
            signal=EmergenceSignal.SERENDIPITOUS_FIND,
            agents_involved=agents_involved,
            pattern_signature=f"serendipity:{'|'.join(sorted(novel_keys))}",
            narrative=f"Serendipitous discovery of novel context keys: {', '.join(novel_keys)}",
            significance=significance,
            context={"novel_keys": novel_keys},
        )

    def log_innovation(
        self,
        description: str,
        agents_involved: List[str],
        significance: float = 0.5,
    ) -> None:
        self._innovation_log.append({
            "description": description,
            "agents_involved": list(agents_involved),
            "significance": significance,
            "timestamp": _time_module.time(),
        })

    def get_traces(
        self,
        signal: Optional[EmergenceSignal] = None,
        min_significance: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        results = self._traces
        if signal is not None:
            results = [t for t in results if t.signal == signal]
        results = [t for t in results if t.significance >= min_significance]
        results.sort(key=lambda t: t.significance, reverse=True)
        return [t.to_dict() for t in results[:limit]]

    def get_innovations(self, limit: int = 20) -> List[Dict[str, Any]]:
        items = list(self._innovation_log)
        return items[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        signal_counts: Dict[str, int] = defaultdict(int)
        for t in self._traces:
            signal_counts[t.signal.value] += 1
        return {
            "total_traces": len(self._traces),
            "activity_stream_size": len(self._activity_stream),
            "tracked_agents": len(self._agent_patterns),
            "unique_signatures": len(self._collective_signatures),
            "innovation_log_size": len(self._innovation_log),
            "signal_counts": dict(signal_counts),
            "avg_significance": sum(t.significance for t in self._traces) / max(1, len(self._traces)),
        }

    def reset(self) -> None:
        self._traces.clear()
        self._activity_stream.clear()
        self._agent_patterns.clear()
        self._collective_signatures.clear()
        self._innovation_log.clear()


# ---------------------------------------------------------------------------
# SwarmIntelligenceEngine (Singleton)
# ---------------------------------------------------------------------------


class SwarmIntelligenceEngine:
    """Central orchestrator for collective swarm intelligence.

    Manages agent registration, task distribution, consensus building,
    knowledge sharing, and emergent behavior detection. Acts as the
    single entry point for all swarm coordination activities within
    the SparkLabs game creation pipeline.

    Usage:
        engine = get_swarm_intelligence()
        agent = engine.register_agent("designer_1", "Alice",
                                       capabilities=["level_design", "pacing"])
        tasklet = engine.submit_task("Design Boss Arena",
                                      "Create a multi-phase boss arena layout",
                                      required_capabilities=["level_design"])
        ballot = engine.open_consensus("Boss Difficulty",
                                        "What difficulty tier?",
                                        ["easy", "medium", "hard"])
        engine.contribute_knowledge("boss:arena_size", "large",
                                     "designer_1", tags=["boss", "arena"])
    """

    _instance: Optional[SwarmIntelligenceEngine] = None
    _lock: threading.RLock = threading.RLock()

    MAX_AGENTS = 200
    MAX_TASKLETS = 1000
    MAX_GRANULES = 2000

    def __new__(cls) -> SwarmIntelligenceEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._agents: Dict[str, SwarmAgent] = {}
                    instance._compiler = ConsensusCompiler()
                    instance._disperser = TaskDisperser()
                    instance._reservoir = InsightReservoir(max_granules=cls.MAX_GRANULES)
                    instance._oracle = PatternOracle()
                    instance._event_log: Deque[Dict[str, Any]] = deque(maxlen=1000)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> SwarmIntelligenceEngine:
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

    # ------------------------------------------------------------------
    # Agent Management
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        moniker: str = "",
        capabilities: Optional[List[str]] = None,
        capacity: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwarmAgent:
        if len(self._agents) >= self.MAX_AGENTS:
            oldest = min(self._agents.values(), key=lambda a: a.last_heartbeat)
            del self._agents[oldest.id]

        agent = SwarmAgent(
            agent_id=agent_id,
            moniker=moniker or agent_id,
            capabilities=capabilities or [],
            capacity=capacity,
            metadata=metadata or {},
        )
        self._agents[agent.id] = agent
        self._event_log.append({
            "event": "agent_registered",
            "agent_id": agent.id,
            "moniker": agent.moniker,
            "capabilities": list(agent.capabilities),
            "timestamp": _time_module.time(),
        })
        return agent

    def unregister_agent(self, agent_id: str) -> bool:
        for aid, agent in list(self._agents.items()):
            if agent.agent_id == agent_id or agent.id == agent_id:
                del self._agents[aid]
                self._event_log.append({
                    "event": "agent_unregistered",
                    "agent_id": agent.id,
                    "moniker": agent.moniker,
                    "timestamp": _time_module.time(),
                })
                return True
        return False

    def heartbeat(self, agent_id: str) -> bool:
        for agent in self._agents.values():
            if agent.agent_id == agent_id or agent.id == agent_id:
                if agent.disposition == AgentDisposition.OFFLINE:
                    agent.disposition = AgentDisposition.AVAILABLE
                agent.last_heartbeat = _time_module.time()
                return True
        return False

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        for agent in self._agents.values():
            if agent.agent_id == agent_id or agent.id == agent_id:
                return agent.to_dict()
        return None

    def list_agents(
        self,
        disposition: Optional[AgentDisposition] = None,
        capability: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = list(self._agents.values())
        if disposition is not None:
            results = [a for a in results if a.disposition == disposition]
        if capability is not None:
            results = [a for a in results if capability in a.capabilities]
        return [a.to_dict() for a in results]

    def update_agent_reputation(self, agent_id: str, delta: float) -> bool:
        for agent in self._agents.values():
            if agent.agent_id == agent_id or agent.id == agent_id:
                agent.reputation = max(0.0, min(2.0, agent.reputation + delta))
                return True
        return False

    # ------------------------------------------------------------------
    # Task Distribution
    # ------------------------------------------------------------------

    def submit_task(
        self,
        title: str,
        description: str,
        required_capabilities: Optional[List[str]] = None,
        urgency: str = "medium",
        dependencies: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        max_attempts: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwarmTasklet:
        try:
            urgency_enum = TaskUrgency(urgency)
        except ValueError:
            urgency_enum = TaskUrgency.MEDIUM

        tasklet = self._disperser.submit_tasklet(
            title=title,
            description=description,
            required_capabilities=required_capabilities,
            urgency=urgency_enum,
            dependencies=dependencies,
            parent_id=parent_id,
            max_attempts=max_attempts,
            metadata=metadata,
        )
        self._event_log.append({
            "event": "task_submitted",
            "tasklet_id": tasklet.id,
            "title": tasklet.title,
            "urgency": tasklet.urgency.value,
            "timestamp": _time_module.time(),
        })
        return tasklet

    def dispatch_ready_tasks(self) -> List[Dict[str, Any]]:
        """Match all ready tasklets to available agents and dispatch them."""
        dispatched: List[Dict[str, Any]] = []
        ready = self._disperser.get_ready_tasklets()
        for tasklet in ready:
            matched_agent_id = self._disperser.match_to_agent(tasklet.id, self._agents)
            if matched_agent_id:
                self._disperser.dispatch(tasklet.id, matched_agent_id)
                agent = self._agents.get(matched_agent_id)
                if agent:
                    agent.active_load += 1
                    agent.current_task_id = tasklet.id
                    if agent.active_load >= agent.capacity:
                        agent.disposition = AgentDisposition.BUSY
                dispatched.append({
                    "tasklet_id": tasklet.id,
                    "agent_id": matched_agent_id,
                    "title": tasklet.title,
                })
                self._oracle.observe_action(
                    matched_agent_id,
                    f"task_accepted:{tasklet.title}",
                    context={"tasklet_id": tasklet.id, "urgency": tasklet.urgency.value},
                )
        return dispatched

    def complete_task(
        self,
        tasklet_id: str,
        result: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> bool:
        tasklet = self._disperser._tasklets.get(tasklet_id)
        if tasklet is None:
            return False

        agent_id = tasklet.assigned_agent_id
        success = self._disperser.mark_accomplished(tasklet_id, result, confidence)

        if success and agent_id:
            agent = self._agents.get(agent_id)
            if agent:
                agent.active_load = max(0, agent.active_load - 1)
                agent.total_contributions += 1
                agent.successful_contributions += 1
                agent.reputation = min(2.0, agent.reputation + 0.03)
                agent.current_task_id = None
                if agent.active_load < agent.capacity:
                    agent.disposition = AgentDisposition.AVAILABLE

            self._oracle.observe_action(
                agent_id,
                f"task_completed:{tasklet.title}",
                context={"tasklet_id": tasklet_id, "confidence": confidence},
            )

        self._event_log.append({
            "event": "task_completed",
            "tasklet_id": tasklet_id,
            "agent_id": agent_id,
            "success": success,
            "timestamp": _time_module.time(),
        })

        return success

    def fail_task(self, tasklet_id: str) -> bool:
        tasklet = self._disperser._tasklets.get(tasklet_id)
        if tasklet is None:
            return False

        agent_id = tasklet.assigned_agent_id
        was_reassigned = self._disperser.mark_faulted(tasklet_id)

        if agent_id:
            agent = self._agents.get(agent_id)
            if agent:
                agent.active_load = max(0, agent.active_load - 1)
                agent.total_contributions += 1
                agent.reputation = max(0.0, agent.reputation - 0.05)
                agent.current_task_id = None
                if agent.active_load < agent.capacity:
                    agent.disposition = AgentDisposition.AVAILABLE

            self._oracle.observe_action(
                agent_id,
                f"task_failed:{tasklet.title}",
                context={"tasklet_id": tasklet_id, "reassigned": was_reassigned},
            )

        self._event_log.append({
            "event": "task_failed",
            "tasklet_id": tasklet_id,
            "agent_id": agent_id,
            "reassigned": tasklet.outcome == TaskOutcome.REASSIGNED,
            "timestamp": _time_module.time(),
        })

        return was_reassigned

    def get_task(self, tasklet_id: str) -> Optional[Dict[str, Any]]:
        return self._disperser.get_tasklet(tasklet_id)

    # ------------------------------------------------------------------
    # Consensus Building
    # ------------------------------------------------------------------

    def open_consensus(
        self,
        topic: str,
        description: str,
        options: List[str],
        protocol: str = "trust_weighted",
        max_rounds: int = 5,
        leader_id: Optional[str] = None,
    ) -> ConsensusBallot:
        try:
            protocol_enum = VoteProtocol(protocol)
        except ValueError:
            protocol_enum = VoteProtocol.TRUST_WEIGHTED

        ballot = self._compiler.initiate_ballot(
            topic=topic,
            description=description,
            options=options,
            protocol=protocol_enum,
            max_rounds=max_rounds,
            leader_id=leader_id,
        )
        self._event_log.append({
            "event": "consensus_opened",
            "ballot_id": ballot.ballot_id,
            "topic": topic,
            "protocol": protocol_enum.value,
            "timestamp": _time_module.time(),
        })
        return ballot

    def cast_consensus_vote(
        self,
        ballot_id: str,
        voter_id: str,
        option: str,
    ) -> bool:
        agent = self._find_agent_by_id(voter_id)
        weight = agent.reputation if agent else 1.0
        success = self._compiler.cast_vote(ballot_id, voter_id, option, weight)
        if success:
            self._event_log.append({
                "event": "vote_cast",
                "ballot_id": ballot_id,
                "voter_id": voter_id,
                "option": option,
                "weight": weight,
                "timestamp": _time_module.time(),
            })
        return success

    def tally_consensus(self, ballot_id: str) -> Optional[Dict[str, Any]]:
        ballot = self._compiler.tally(ballot_id)
        if ballot is None:
            return None
        self._event_log.append({
            "event": "consensus_tallied",
            "ballot_id": ballot_id,
            "phase": ballot.phase.value,
            "winner": ballot.winning_option,
            "deadlocked": ballot.deadlocked,
            "timestamp": _time_module.time(),
        })
        return ballot.to_dict()

    def break_consensus_stalemate(self, ballot_id: str, tiebreaker: str = "highest_confidence") -> Optional[Dict[str, Any]]:
        ballot = self._compiler.break_stalemate(ballot_id, tiebreaker)
        if ballot is None:
            return None
        return ballot.to_dict()

    def get_ballot(self, ballot_id: str) -> Optional[Dict[str, Any]]:
        return self._compiler.get_ballot(ballot_id)

    # ------------------------------------------------------------------
    # Knowledge Sharing
    # ------------------------------------------------------------------

    def contribute_knowledge(
        self,
        key: str,
        value: Any,
        contributor_id: str,
        category: str = "observation",
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        ttl: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeGranule:
        try:
            category_enum = KnowledgeCategory(category)
        except ValueError:
            category_enum = KnowledgeCategory.OBSERVATION

        granule = self._reservoir.contribute(
            key=key,
            value=value,
            contributor_id=contributor_id,
            category=category_enum,
            confidence=confidence,
            tags=tags,
            ttl=ttl,
            metadata=metadata,
        )
        self._event_log.append({
            "event": "knowledge_contributed",
            "key": key,
            "contributor_id": contributor_id,
            "category": category_enum.value,
            "confidence": granule.confidence,
            "version": granule.version,
            "timestamp": _time_module.time(),
        })

        self._oracle.observe_action(
            contributor_id,
            "knowledge_contributed",
            context={"key": key, "category": category_enum.value},
        )

        return granule

    def retrieve_knowledge(self, key: str) -> Optional[Dict[str, Any]]:
        granule = self._reservoir.retrieve(key)
        return granule.to_dict() if granule else None

    def search_knowledge(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        category_enum = None
        if category is not None:
            try:
                category_enum = KnowledgeCategory(category)
            except ValueError:
                pass
        granules = self._reservoir.search(
            query=query,
            tags=tags,
            category=category_enum,
            min_confidence=min_confidence,
            limit=limit,
        )
        return [g.to_dict() for g in granules]

    def refresh_knowledge(self, key: str) -> bool:
        return self._reservoir.refresh(key)

    def get_knowledge_history(self, key: str) -> List[Dict[str, Any]]:
        return self._reservoir.get_version_history(key)

    # ------------------------------------------------------------------
    # Emergence Detection
    # ------------------------------------------------------------------

    def observe_agent_action(
        self,
        agent_id: str,
        action_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._oracle.observe_action(agent_id, action_type, context)

    def analyze_emergence(self) -> List[Dict[str, Any]]:
        traces = self._oracle.analyze()
        for trace in traces:
            self._event_log.append({
                "event": "emergence_detected",
                "trace_id": trace.trace_id,
                "signal": trace.signal.value,
                "significance": trace.significance,
                "timestamp": trace.observed_at,
            })
        return [t.to_dict() for t in traces]

    def log_innovation(
        self,
        description: str,
        agents_involved: List[str],
        significance: float = 0.5,
    ) -> None:
        self._oracle.log_innovation(description, agents_involved, significance)

    def get_emergence_traces(
        self,
        signal: Optional[str] = None,
        min_significance: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        signal_enum = None
        if signal is not None:
            try:
                signal_enum = EmergenceSignal(signal)
            except ValueError:
                pass
        return self._oracle.get_traces(signal=signal_enum, min_significance=min_significance, limit=limit)

    def get_innovations(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._oracle.get_innovations(limit)

    # ------------------------------------------------------------------
    # System Overview
    # ------------------------------------------------------------------

    def get_topology(self) -> Dict[str, Any]:
        return {
            "agent_count": len(self._agents),
            "available_agents": sum(1 for a in self._agents.values() if a.is_available),
            "busy_agents": sum(1 for a in self._agents.values() if a.disposition == AgentDisposition.BUSY),
            "offline_agents": sum(1 for a in self._agents.values() if a.disposition == AgentDisposition.OFFLINE),
            "task_stats": self._disperser.get_stats(),
            "avg_reputation": sum(a.reputation for a in self._agents.values()) / max(1, len(self._agents)),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agents": {
                "total": len(self._agents),
                "available": sum(1 for a in self._agents.values() if a.is_available),
                "busy": sum(1 for a in self._agents.values() if a.disposition == AgentDisposition.BUSY),
                "avg_reputation": sum(a.reputation for a in self._agents.values()) / max(1, len(self._agents)),
                "total_contributions": sum(a.total_contributions for a in self._agents.values()),
            },
            "compiler": self._compiler.get_stats(),
            "disperser": self._disperser.get_stats(),
            "reservoir": self._reservoir.get_stats(),
            "oracle": self._oracle.get_stats(),
            "event_log_size": len(self._event_log),
        }

    def get_event_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        items = list(self._event_log)
        return items[-limit:]

    def reset(self) -> None:
        self._agents.clear()
        self._compiler.reset()
        self._disperser.reset()
        self._reservoir.reset()
        self._oracle.reset()
        self._event_log.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_agent_by_id(self, agent_id: str) -> Optional[SwarmAgent]:
        for agent in self._agents.values():
            if agent.agent_id == agent_id or agent.id == agent_id:
                return agent
        return None


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_swarm_intelligence() -> SwarmIntelligenceEngine:
    """Return the singleton SwarmIntelligenceEngine instance."""
    return SwarmIntelligenceEngine.get_instance()