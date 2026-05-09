"""
SparkLabs Agent - Agent Negotiation

Multi-agent negotiation protocol for the SparkLabs AI-native game engine.
Enables multiple specialized AI agents (designer, programmer, artist) to
negotiate design decisions, resolve conflicts, and reach consensus on game
development choices. Supports proposal-counterproposal cycles, voting
mechanisms, and tie-breaking arbitration.

Architecture:
  AgentNegotiation
    |-- NegotiationSession (topic, participants, proposals, outcome)
    |-- Proposal (what is proposed, by whom, with justification)
    |-- Vote (agent stance on a proposal with reasoning)
    |-- ConsensusResult (agreed outcome or deadlock detection)
    |-- ArbitrationRule (tie-breaking and deadlock resolution)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VoteStance(Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    ABSTAIN = "abstain"
    CONDITIONAL_SUPPORT = "conditional_support"


class NegotiationPhase(Enum):
    OPENING = "opening"
    PROPOSAL = "proposal"
    DELIBERATION = "deliberation"
    VOTING = "voting"
    RESOLUTION = "resolution"
    CLOSED = "closed"


class ResolutionType(Enum):
    CONSENSUS = "consensus"
    MAJORITY = "majority"
    ARBITRATED = "arbitrated"
    DEADLOCK = "deadlock"
    WITHDRAWN = "withdrawn"


@dataclass
class Proposal:
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: str = ""
    agent_role: str = ""
    title: str = ""
    description: str = ""
    justification: str = ""
    alternatives_considered: List[str] = field(default_factory=list)
    impact_areas: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    withdrawn: bool = False

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "agent": self.agent_name,
            "role": self.agent_role,
            "title": self.title,
            "description": self.description[:300],
            "withdrawn": self.withdrawn,
        }


@dataclass
class Vote:
    vote_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    proposal_id: str = ""
    agent_name: str = ""
    agent_role: str = ""
    stance: VoteStance = VoteStance.ABSTAIN
    reasoning: str = ""
    conditions: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "vote_id": self.vote_id,
            "agent": self.agent_name,
            "stance": self.stance.value,
            "reasoning": self.reasoning[:200],
        }


@dataclass
class ConsensusResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    resolution_type: ResolutionType = ResolutionType.CONSENSUS
    winning_proposal_id: Optional[str] = None
    compromise_description: str = ""
    support_count: int = 0
    oppose_count: int = 0
    abstain_count: int = 0
    resolved_by: str = ""
    resolved_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "topic": self.topic,
            "resolution": self.resolution_type.value,
            "winning_proposal": self.winning_proposal_id,
            "votes": f"{self.support_count} support / {self.oppose_count} oppose / {self.abstain_count} abstain",
        }


@dataclass
class NegotiationSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    description: str = ""
    phase: NegotiationPhase = NegotiationPhase.OPENING
    participants: List[Dict[str, str]] = field(default_factory=list)
    proposals: List[Proposal] = field(default_factory=list)
    votes: List[Vote] = field(default_factory=list)
    result: Optional[ConsensusResult] = None
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    max_rounds: int = 3
    current_round: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_participant(self, name: str, role: str, expertise: str = "") -> None:
        self.participants.append({"name": name, "role": role, "expertise": expertise})

    def propose(self, agent_name: str, agent_role: str, title: str, description: str, justification: str = "", **kwargs) -> Proposal:
        proposal = Proposal(
            agent_name=agent_name,
            agent_role=agent_role,
            title=title,
            description=description,
            justification=justification,
            **kwargs,
        )
        self.proposals.append(proposal)
        if self.phase == NegotiationPhase.OPENING:
            self.phase = NegotiationPhase.PROPOSAL
        return proposal

    def cast_vote(self, agent_name: str, agent_role: str, proposal_id: str, stance: VoteStance, reasoning: str = "", conditions: str = "") -> Vote:
        vote = Vote(
            proposal_id=proposal_id,
            agent_name=agent_name,
            agent_role=agent_role,
            stance=stance,
            reasoning=reasoning,
            conditions=conditions,
        )
        self.votes.append(vote)
        return vote

    def tally(self) -> Dict[str, Dict[str, int]]:
        counts: Dict[str, Dict[str, int]] = {}
        for vote in self.votes:
            if vote.proposal_id not in counts:
                counts[vote.proposal_id] = {"support": 0, "oppose": 0, "abstain": 0, "conditional": 0}
            if vote.stance == VoteStance.SUPPORT:
                counts[vote.proposal_id]["support"] += 1
            elif vote.stance == VoteStance.OPPOSE:
                counts[vote.proposal_id]["oppose"] += 1
            elif vote.stance == VoteStance.CONDITIONAL_SUPPORT:
                counts[vote.proposal_id]["conditional"] += 1
            else:
                counts[vote.proposal_id]["abstain"] += 1
        return counts

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "phase": self.phase.value,
            "participants": len(self.participants),
            "proposals": len(self.proposals),
            "votes": len(self.votes),
            "round": f"{self.current_round}/{self.max_rounds}",
            "result": self.result.to_dict() if self.result else None,
        }


class AgentNegotiation:
    """
    Multi-agent negotiation protocol for collaborative game design.

    Coordinates negotiation sessions where specialized AI agents propose
    design solutions, deliberate, and vote to reach consensus. Supports
    structured proposal cycles with justification, multi-round deliberation,
    weighted voting based on agent expertise, deadlock detection with
    automatic arbitration, and comprehensive session recording for
    design decision provenance.
    """

    _instance: Optional["AgentNegotiation"] = None

    def __init__(self):
        self._active_sessions: Dict[str, NegotiationSession] = {}
        self._session_history: List[NegotiationSession] = []
        self._max_history: int = 50

    @classmethod
    def get_instance(cls) -> "AgentNegotiation":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def open_session(self, topic: str, description: str = "", participants: Optional[List[Dict[str, str]]] = None) -> NegotiationSession:
        session = NegotiationSession(topic=topic, description=description)
        for p in (participants or []):
            session.add_participant(p.get("name", ""), p.get("role", ""), p.get("expertise", ""))
        self._active_sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        return self._active_sessions.get(session_id)

    def advance_phase(self, session_id: str) -> Optional[NegotiationPhase]:
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        transitions = {
            NegotiationPhase.OPENING: NegotiationPhase.PROPOSAL,
            NegotiationPhase.PROPOSAL: NegotiationPhase.DELIBERATION,
            NegotiationPhase.DELIBERATION: NegotiationPhase.VOTING,
            NegotiationPhase.VOTING: NegotiationPhase.RESOLUTION,
            NegotiationPhase.RESOLUTION: NegotiationPhase.CLOSED,
        }

        next_phase = transitions.get(session.phase)
        if next_phase:
            session.phase = next_phase
            if next_phase == NegotiationPhase.VOTING:
                session.current_round += 1
        return next_phase

    def resolve_session(self, session_id: str, method: str = "majority") -> Optional[ConsensusResult]:
        session = self._active_sessions.get(session_id)
        if not session or not session.proposals:
            return None

        tally = session.tally()
        if not tally:
            session.result = ConsensusResult(
                topic=session.topic,
                resolution_type=ResolutionType.WITHDRAWN,
            )
            self._close_session(session)
            return session.result

        best_proposal_id = max(tally, key=lambda pid: tally[pid]["support"] - tally[pid]["oppose"])
        best_counts = tally[best_proposal_id]
        total_votes = sum(best_counts.values())

        support = best_counts["support"]
        oppose = best_counts["oppose"]
        abstain = best_counts["abstain"]

        if support > oppose and support > len(session.participants) * 0.6:
            resolution = ResolutionType.CONSENSUS
        elif support > oppose:
            resolution = ResolutionType.MAJORITY
        elif method == "arbitrate":
            resolution = ResolutionType.ARBITRATED
        else:
            resolution = ResolutionType.DEADLOCK

        session.result = ConsensusResult(
            topic=session.topic,
            resolution_type=resolution,
            winning_proposal_id=best_proposal_id,
            support_count=support,
            oppose_count=oppose,
            abstain_count=abstain,
            resolved_by="vote",
        )

        self._close_session(session)
        return session.result

    def list_sessions(self, active_only: bool = True) -> List[NegotiationSession]:
        if active_only:
            return list(self._active_sessions.values())
        return list(self._active_sessions.values()) + self._session_history

    def _close_session(self, session: NegotiationSession) -> None:
        session.phase = NegotiationPhase.CLOSED
        session.ended_at = time.time()
        if session.session_id in self._active_sessions:
            del self._active_sessions[session.session_id]
        self._session_history.append(session)
        if len(self._session_history) > self._max_history:
            self._session_history = self._session_history[-self._max_history:]

    def get_stats(self) -> dict:
        total_proposals = sum(len(s.proposals) for s in self._session_history)
        total_votes = sum(len(s.votes) for s in self._session_history)
        resolutions = {}
        for s in self._session_history:
            if s.result:
                rt = s.result.resolution_type.value
                resolutions[rt] = resolutions.get(rt, 0) + 1
        return {
            "active_sessions": len(self._active_sessions),
            "completed_sessions": len(self._session_history),
            "total_proposals": total_proposals,
            "total_votes": total_votes,
            "resolution_breakdown": resolutions,
        }

    def reset(self) -> None:
        self._active_sessions.clear()
        self._session_history.clear()


def get_agent_negotiation() -> AgentNegotiation:
    return AgentNegotiation.get_instance()
