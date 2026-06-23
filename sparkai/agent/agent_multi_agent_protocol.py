"""
SparkLabs Agent - Multi-Agent Protocol

Enables advanced collaboration between multiple AI agents through structured
communication protocols, role negotiation, task delegation, and consensus
building. Provides a unified framework for multi-agent communication patterns
including request-response, publish-subscribe, broadcast, negotiation,
delegation, and consensus-based coordination.

Architecture:
    MultiAgentProtocolEngine (singleton per name)
      |-- AgentIdentity (registered agent with role and capabilities)
      |-- ProtocolMessage (typed inter-agent communication)
      |-- TaskDelegation (delegated work with lifecycle tracking)
      |-- ConsensusProposal (voting-based agreement mechanism)
      |-- CollaborationSession (multi-agent workspace)
      |-- Negotiation (bilateral agreement protocol)

Agent Roles:
    - COORDINATOR: orchestrates workflow and assigns tasks
    - WORKER: executes delegated tasks and produces output
    - OBSERVER: monitors communication without active participation
    - MEDIATOR: resolves conflicts and facilitates agreement
    - SPECIALIST: provides domain-specific expertise
    - FACILITATOR: manages group processes and collaboration

Protocol Types:
    - REQUEST_RESPONSE: point-to-point synchronous request/reply
    - PUBLISH_SUBSCRIBE: topic-based event distribution
    - BROADCAST: one-to-all message propagation
    - NEGOTIATION: bilateral offer/counter-offer exchange
    - DELEGATION: task assignment with acceptance workflow
    - CONSENSUS: multi-party voting and agreement

Usage:
    protocol = get_multi_agent_protocol("game_studio")
    agent = protocol.register_agent("designer_1", AgentRole.COORDINATOR,
                                     ["game_design", "level_design"])
    msg = protocol.send_message(ProtocolType.REQUEST_RESPONSE,
                                "designer_1", "designer_2",
                                "Review Level Layout", "Please review the boss arena design")
    delegation = protocol.create_delegation("Implement boss AI behavior tree",
                                            "designer_1", "programmer_1",
                                            ["ai", "behavior_tree"], 3600)
    proposal = protocol.propose_consensus("Should we use procedural generation?",
                                          "designer_1",
                                          ConsensusAlgorithm.MAJORITY_VOTE,
                                          ["procedural", "handcrafted", "hybrid"])
    negotiation = protocol.start_negotiation("designer_1", "programmer_1",
                                             "Boss HP Balance")
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

_time_module = time


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class AgentRole(Enum):
    """Roles that agents can fulfill in multi-agent collaboration."""

    COORDINATOR = "coordinator"
    WORKER = "worker"
    OBSERVER = "observer"
    MEDIATOR = "mediator"
    SPECIALIST = "specialist"
    FACILITATOR = "facilitator"


class ProtocolType(Enum):
    """Communication protocols for inter-agent message exchange."""

    REQUEST_RESPONSE = "request_response"
    PUBLISH_SUBSCRIBE = "publish_subscribe"
    BROADCAST = "broadcast"
    NEGOTIATION = "negotiation"
    DELEGATION = "delegation"
    CONSENSUS = "consensus"


class MessageStatus(Enum):
    """Lifecycle states for protocol messages."""

    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    RESPONDED = "responded"
    FAILED = "failed"
    EXPIRED = "expired"


class ConsensusAlgorithm(Enum):
    """Voting and agreement algorithms for multi-agent consensus."""

    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    RANKED_CHOICE = "ranked_choice"
    UNANIMOUS = "unanimous"
    DELEGATED = "delegated"


class NegotiationPhase(Enum):
    """Phases in a bilateral negotiation between two agents."""

    PROPOSAL = "proposal"
    COUNTER_PROPOSAL = "counter_proposal"
    EVALUATION = "evaluation"
    ACCEPTANCE = "acceptance"
    REJECTION = "rejection"
    COMMITMENT = "commitment"


class DelegationStatus(Enum):
    """Lifecycle states for task delegation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProposalStatus(Enum):
    """Lifecycle states for a consensus proposal."""

    OPEN = "open"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    TIED = "tied"


class NegotiationStatus(Enum):
    """Lifecycle states for a negotiation session."""

    ACTIVE = "active"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEADLOCKED = "deadlocked"
    CANCELLED = "cancelled"
    COMMITTED = "committed"


class SessionState(Enum):
    """Runtime states for a collaboration session."""

    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class AgentIdentity:
    """Registration record for an agent participating in the protocol.

    Each agent has a unique ID, a designated role, a set of capabilities,
    and tracks its current status alongside join metadata.
    """

    id: str = ""
    name: str = ""
    role: AgentRole = AgentRole.WORKER
    capabilities: List[str] = field(default_factory=list)
    status: str = "active"
    joined_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "status": self.status,
            "joined_at": self.joined_at,
            "metadata": self.metadata,
        }


@dataclass
class ProtocolMessage:
    """A structured message exchanged between agents via a protocol.

    Messages carry typed content with priority, TTL, and optional reply-to
    references to form conversational threads across protocol types.
    """

    id: str = ""
    protocol_type: ProtocolType = ProtocolType.REQUEST_RESPONSE
    sender_id: str = ""
    recipient_id: str = ""
    subject: str = ""
    body: str = ""
    priority: int = 0
    status: MessageStatus = MessageStatus.DRAFT
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reply_to: Optional[str] = None
    ttl: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "protocol_type": self.protocol_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "subject": self.subject,
            "body": self.body[:500],
            "priority": self.priority,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "ttl": self.ttl,
        }

    @property
    def is_expired(self) -> bool:
        return self.status == MessageStatus.EXPIRED

    @property
    def is_delivered(self) -> bool:
        return self.status in (
            MessageStatus.DELIVERED,
            MessageStatus.READ,
            MessageStatus.RESPONDED,
        )


@dataclass
class TaskDelegation:
    """A unit of work delegated from one agent to another.

    Delegations track requirements, deadlines, status transitions, and
    final results through a complete lifecycle from pending to completion
    or failure.
    """

    id: str = ""
    task_description: str = ""
    delegator_id: str = ""
    delegate_id: str = ""
    requirements: List[str] = field(default_factory=list)
    deadline: Optional[float] = None
    status: DelegationStatus = DelegationStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_description": self.task_description[:300],
            "delegator_id": self.delegator_id,
            "delegate_id": self.delegate_id,
            "requirements": self.requirements,
            "deadline": self.deadline,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at,
        }

    @property
    def is_active(self) -> bool:
        return self.status in (
            DelegationStatus.PENDING,
            DelegationStatus.ACCEPTED,
            DelegationStatus.IN_PROGRESS,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            DelegationStatus.COMPLETED,
            DelegationStatus.FAILED,
            DelegationStatus.CANCELLED,
        )


@dataclass
class ConsensusProposal:
    """A proposal submitted for multi-agent voting and agreement.

    Supports multiple consensus algorithms, tracks individual votes,
    and determines the final outcome based on the configured algorithm.
    """

    id: str = ""
    proposal: str = ""
    proposer_id: str = ""
    algorithm: ConsensusAlgorithm = ConsensusAlgorithm.MAJORITY_VOTE
    options: List[str] = field(default_factory=list)
    votes: Dict[str, str] = field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.OPEN
    deadline: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "proposal": self.proposal[:300],
            "proposer_id": self.proposer_id,
            "algorithm": self.algorithm.value,
            "options": self.options,
            "votes": self.votes,
            "vote_count": len(self.votes),
            "status": self.status.value,
            "deadline": self.deadline,
            "result": self.result,
            "created_at": self.created_at,
        }

    def tally_votes(self) -> Dict[str, int]:
        """Count votes per option."""
        counts: Dict[str, int] = {}
        for choice in self.votes.values():
            counts[choice] = counts.get(choice, 0) + 1
        return counts

    def resolve(self) -> Optional[str]:
        """Resolve the proposal using the configured consensus algorithm.

        Returns:
            The winning option string, or None if no resolution is possible.
        """
        tally = self.tally_votes()
        if not tally:
            return None

        if self.algorithm == ConsensusAlgorithm.MAJORITY_VOTE:
            total = sum(tally.values())
            winner = max(tally, key=tally.get)
            if tally[winner] > total / 2:
                return winner
            return None

        elif self.algorithm == ConsensusAlgorithm.WEIGHTED_VOTE:
            return max(tally, key=tally.get)

        elif self.algorithm == ConsensusAlgorithm.RANKED_CHOICE:
            total = sum(tally.values())
            winner = max(tally, key=tally.get)
            if tally[winner] >= total * 0.6:
                return winner
            return None

        elif self.algorithm == ConsensusAlgorithm.UNANIMOUS:
            if len(set(self.votes.values())) == 1 and len(self.votes) > 0:
                return list(self.votes.values())[0]
            return None

        elif self.algorithm == ConsensusAlgorithm.DELEGATED:
            return max(tally, key=tally.get)

        return None


@dataclass
class CollaborationSession:
    """A multi-agent workspace binding participants, protocol, and messages.

    Each session operates under a specific protocol type, maintains the
    roster of participating agents, and records the full message history
    alongside runtime state transitions.
    """

    id: str = ""
    session_type: str = ""
    participants: List[str] = field(default_factory=list)
    protocol: ProtocolType = ProtocolType.REQUEST_RESPONSE
    state: SessionState = SessionState.CREATED
    messages: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_type": self.session_type,
            "participants": self.participants,
            "participant_count": self.participant_count,
            "protocol": self.protocol.value,
            "state": self.state.value,
            "message_count": self.message_count,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_participant(self, agent_id: str) -> bool:
        if agent_id not in self.participants:
            self.participants.append(agent_id)
            self.updated_at = datetime.utcnow().isoformat()
            return True
        return False

    def remove_participant(self, agent_id: str) -> bool:
        if agent_id in self.participants:
            self.participants.remove(agent_id)
            self.updated_at = datetime.utcnow().isoformat()
            return True
        return False


@dataclass
class Negotiation:
    """A bilateral negotiation between two agents over a specific topic.

    Tracks the negotiation phase, offer history, and final agreement
    through a structured proposal/counter-proposal workflow.
    """

    id: str = ""
    phase: NegotiationPhase = NegotiationPhase.PROPOSAL
    initiator_id: str = ""
    respondent_id: str = ""
    topic: str = ""
    offers: List[Dict[str, Any]] = field(default_factory=list)
    status: NegotiationStatus = NegotiationStatus.ACTIVE
    agreement: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def offer_count(self) -> int:
        return len(self.offers)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase.value,
            "initiator_id": self.initiator_id,
            "respondent_id": self.respondent_id,
            "topic": self.topic,
            "offers": self.offers,
            "offer_count": self.offer_count,
            "status": self.status.value,
            "agreement": self.agreement,
            "created_at": self.created_at,
        }

    def add_offer(self, agent_id: str, offer: Dict[str, Any]) -> None:
        """Record an offer from an agent in the negotiation."""
        self.offers.append({
            "agent_id": agent_id,
            "offer": offer,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if self.phase == NegotiationPhase.PROPOSAL:
            self.phase = NegotiationPhase.COUNTER_PROPOSAL
        elif self.phase == NegotiationPhase.COUNTER_PROPOSAL:
            self.phase = NegotiationPhase.EVALUATION


# ------------------------------------------------------------------
# MultiAgentProtocolEngine
# ------------------------------------------------------------------


class MultiAgentProtocolEngine:
    """Singleton-per-name multi-agent protocol engine for AI agent collaboration.

    Provides structured communication protocols, role negotiation, task
    delegation, and consensus building across multiple AI agents. Each
    named instance maintains its own isolated state for agents, messages,
    delegations, proposals, negotiations, and sessions.

    Thread-safe via RLock. All public methods acquire the lock before
    reading or modifying internal state. Use get_multi_agent_protocol(name)
    to obtain a named singleton instance.
    """

    _instances: Dict[str, "MultiAgentProtocolEngine"] = {}
    _lock: threading.RLock = threading.RLock()

    MAX_AGENTS = 200
    MAX_MESSAGES = 5000
    MAX_DELEGATIONS = 500
    MAX_PROPOSALS = 200
    MAX_NEGOTIATIONS = 200
    MAX_SESSIONS = 100
    MAX_MESSAGE_HISTORY = 1000

    def __new__(cls, name: str = "default") -> "MultiAgentProtocolEngine":
        with cls._lock:
            if name not in cls._instances:
                instance = super().__new__(cls)
                instance._name = name
                instance._agents: Dict[str, AgentIdentity] = {}
                instance._messages: Dict[str, ProtocolMessage] = {}
                instance._delegations: Dict[str, TaskDelegation] = {}
                instance._proposals: Dict[str, ConsensusProposal] = {}
                instance._negotiations: Dict[str, Negotiation] = {}
                instance._sessions: Dict[str, CollaborationSession] = {}
                instance._message_history: Deque[str] = deque(maxlen=cls.MAX_MESSAGE_HISTORY)
                instance._stats: Dict[str, int] = {
                    "total_agents_registered": 0,
                    "total_agents_unregistered": 0,
                    "total_messages_sent": 0,
                    "total_delegations_created": 0,
                    "total_delegations_completed": 0,
                    "total_proposals_created": 0,
                    "total_proposals_resolved": 0,
                    "total_negotiations_started": 0,
                    "total_negotiations_resolved": 0,
                    "total_sessions_created": 0,
                }
                cls._instances[name] = instance
        return cls._instances[name]

    @classmethod
    def get_instance(cls, name: str = "default") -> "MultiAgentProtocolEngine":
        return cls(name)

    # ------------------------------------------------------------------
    # Agent Registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        name: str,
        role: AgentRole = AgentRole.WORKER,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentIdentity:
        """Register a new agent in the protocol engine.

        Args:
            name: Human-readable agent name.
            role: The agent's role in collaborations.
            capabilities: List of capability strings.
            metadata: Optional key-value metadata.

        Returns:
            The newly created AgentIdentity.

        Raises:
            RuntimeError: If the maximum agent count is exceeded.
        """
        with self._lock:
            if len(self._agents) >= self.MAX_AGENTS:
                raise RuntimeError(
                    f"Maximum agent count ({self.MAX_AGENTS}) exceeded"
                )

            agent_id = uuid.uuid4().hex
            agent = AgentIdentity(
                id=agent_id,
                name=name,
                role=role,
                capabilities=capabilities or [],
                metadata=metadata or {},
            )
            self._agents[agent_id] = agent
            self._stats["total_agents_registered"] += 1
            return agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the protocol engine.

        Args:
            agent_id: The agent identifier to remove.

        Returns:
            True if the agent was found and removed, False otherwise.
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                self._stats["total_agents_unregistered"] += 1
                return True
            return False

    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        """Retrieve a registered agent by ID.

        Args:
            agent_id: The agent identifier.

        Returns:
            The AgentIdentity if found, None otherwise.
        """
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentIdentity]:
        """List all registered agents.

        Returns:
            A list of all AgentIdentity instances.
        """
        with self._lock:
            return list(self._agents.values())

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(
        self,
        protocol_type: ProtocolType = ProtocolType.REQUEST_RESPONSE,
        sender_id: str = "",
        recipient_id: str = "",
        subject: str = "",
        body: str = "",
        priority: int = 0,
        ttl: Optional[int] = None,
    ) -> ProtocolMessage:
        """Send a protocol message from one agent to another.

        Args:
            protocol_type: The communication protocol to use.
            sender_id: ID of the sending agent.
            recipient_id: ID of the receiving agent.
            subject: Message subject line.
            body: Message body content.
            priority: Numeric priority (higher = more urgent).
            ttl: Optional time-to-live in seconds.

        Returns:
            The created ProtocolMessage.

        Raises:
            ValueError: If sender or recipient is not registered.
            RuntimeError: If the maximum message count is exceeded.
        """
        with self._lock:
            if sender_id and sender_id not in self._agents:
                raise ValueError(f"Sender agent '{sender_id}' is not registered")
            if recipient_id and recipient_id not in self._agents:
                raise ValueError(f"Recipient agent '{recipient_id}' is not registered")

            if len(self._messages) >= self.MAX_MESSAGES:
                raise RuntimeError(
                    f"Maximum message count ({self.MAX_MESSAGES}) exceeded"
                )

            message_id = uuid.uuid4().hex
            message = ProtocolMessage(
                id=message_id,
                protocol_type=protocol_type,
                sender_id=sender_id,
                recipient_id=recipient_id,
                subject=subject,
                body=body,
                priority=priority,
                status=MessageStatus.SENT,
                ttl=ttl,
            )
            self._messages[message_id] = message
            self._message_history.append(message_id)
            self._stats["total_messages_sent"] += 1
            return message

    def get_messages(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[ProtocolMessage]:
        """Retrieve messages for a specific agent.

        Args:
            agent_id: The agent whose messages to retrieve.
            limit: Maximum number of messages to return.

        Returns:
            A list of ProtocolMessages where the agent is sender or recipient,
            ordered by most recent first.
        """
        with self._lock:
            messages = [
                m for m in self._messages.values()
                if m.sender_id == agent_id or m.recipient_id == agent_id
            ]
            messages.sort(
                key=lambda m: m.timestamp,
                reverse=True,
            )
            return messages[:limit]

    def update_message_status(
        self,
        message_id: str,
        status: MessageStatus,
    ) -> bool:
        """Update the status of a protocol message.

        Args:
            message_id: The message identifier.
            status: The new status to set.

        Returns:
            True if the message was found and updated, False otherwise.
        """
        with self._lock:
            message = self._messages.get(message_id)
            if message is None:
                return False
            message.status = status
            return True

    # ------------------------------------------------------------------
    # Task Delegation
    # ------------------------------------------------------------------

    def create_delegation(
        self,
        task_description: str,
        delegator_id: str,
        delegate_id: str,
        requirements: Optional[List[str]] = None,
        deadline: Optional[float] = None,
    ) -> TaskDelegation:
        """Create a new task delegation from one agent to another.

        Args:
            task_description: Human-readable description of the task.
            delegator_id: ID of the agent delegating the task.
            delegate_id: ID of the agent receiving the task.
            requirements: List of requirement strings.
            deadline: Optional deadline as a Unix timestamp.

        Returns:
            The created TaskDelegation.

        Raises:
            ValueError: If delegator or delegate is not registered.
            RuntimeError: If the maximum delegation count is exceeded.
        """
        with self._lock:
            if delegator_id not in self._agents:
                raise ValueError(f"Delegator agent '{delegator_id}' is not registered")
            if delegate_id not in self._agents:
                raise ValueError(f"Delegate agent '{delegate_id}' is not registered")

            if len(self._delegations) >= self.MAX_DELEGATIONS:
                raise RuntimeError(
                    f"Maximum delegation count ({self.MAX_DELEGATIONS}) exceeded"
                )

            delegation_id = uuid.uuid4().hex
            delegation = TaskDelegation(
                id=delegation_id,
                task_description=task_description,
                delegator_id=delegator_id,
                delegate_id=delegate_id,
                requirements=requirements or [],
                deadline=deadline,
            )
            self._delegations[delegation_id] = delegation
            self._stats["total_delegations_created"] += 1
            return delegation

    def accept_delegation(self, delegation_id: str) -> bool:
        """Accept a pending delegation.

        Args:
            delegation_id: The delegation identifier.

        Returns:
            True if the delegation was accepted, False otherwise.
        """
        with self._lock:
            delegation = self._delegations.get(delegation_id)
            if delegation is None:
                return False
            if delegation.status != DelegationStatus.PENDING:
                return False
            delegation.status = DelegationStatus.ACCEPTED
            return True

    def complete_delegation(
        self,
        delegation_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a delegation as completed with an optional result.

        Args:
            delegation_id: The delegation identifier.
            result: Optional result dictionary.

        Returns:
            True if the delegation was completed, False otherwise.
        """
        with self._lock:
            delegation = self._delegations.get(delegation_id)
            if delegation is None:
                return False
            if delegation.status not in (
                DelegationStatus.ACCEPTED,
                DelegationStatus.IN_PROGRESS,
            ):
                return False
            delegation.status = DelegationStatus.COMPLETED
            delegation.result = result or {}
            self._stats["total_delegations_completed"] += 1
            return True

    def fail_delegation(
        self,
        delegation_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a delegation as failed.

        Args:
            delegation_id: The delegation identifier.
            result: Optional error details dictionary.

        Returns:
            True if the delegation was marked as failed, False otherwise.
        """
        with self._lock:
            delegation = self._delegations.get(delegation_id)
            if delegation is None:
                return False
            if not delegation.is_active:
                return False
            delegation.status = DelegationStatus.FAILED
            delegation.result = result or {}
            return True

    def cancel_delegation(self, delegation_id: str) -> bool:
        """Cancel a pending or active delegation.

        Args:
            delegation_id: The delegation identifier.

        Returns:
            True if the delegation was cancelled, False otherwise.
        """
        with self._lock:
            delegation = self._delegations.get(delegation_id)
            if delegation is None:
                return False
            if not delegation.is_active:
                return False
            delegation.status = DelegationStatus.CANCELLED
            return True

    def get_delegation(self, delegation_id: str) -> Optional[TaskDelegation]:
        """Retrieve a delegation by ID.

        Args:
            delegation_id: The delegation identifier.

        Returns:
            The TaskDelegation if found, None otherwise.
        """
        with self._lock:
            return self._delegations.get(delegation_id)

    def list_delegations(
        self,
        agent_id: Optional[str] = None,
        status: Optional[DelegationStatus] = None,
    ) -> List[TaskDelegation]:
        """List delegations with optional agent and status filters.

        Args:
            agent_id: Filter by delegator or delegate.
            status: Filter by delegation status.

        Returns:
            A filtered list of TaskDelegations.
        """
        with self._lock:
            delegations = list(self._delegations.values())
            if agent_id:
                delegations = [
                    d for d in delegations
                    if d.delegator_id == agent_id or d.delegate_id == agent_id
                ]
            if status:
                delegations = [d for d in delegations if d.status == status]
            return delegations

    # ------------------------------------------------------------------
    # Consensus Proposals
    # ------------------------------------------------------------------

    def propose_consensus(
        self,
        proposal: str,
        proposer_id: str,
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.MAJORITY_VOTE,
        options: Optional[List[str]] = None,
        deadline: Optional[float] = None,
    ) -> ConsensusProposal:
        """Create a new consensus proposal for multi-agent voting.

        Args:
            proposal: Human-readable proposal description.
            proposer_id: ID of the agent making the proposal.
            algorithm: The consensus algorithm to use for resolution.
            options: List of vote options available.
            deadline: Optional deadline as a Unix timestamp.

        Returns:
            The created ConsensusProposal.

        Raises:
            ValueError: If the proposer is not registered.
            RuntimeError: If the maximum proposal count is exceeded.
        """
        with self._lock:
            if proposer_id not in self._agents:
                raise ValueError(f"Proposer agent '{proposer_id}' is not registered")

            if len(self._proposals) >= self.MAX_PROPOSALS:
                raise RuntimeError(
                    f"Maximum proposal count ({self.MAX_PROPOSALS}) exceeded"
                )

            proposal_id = uuid.uuid4().hex
            consensus = ConsensusProposal(
                id=proposal_id,
                proposal=proposal,
                proposer_id=proposer_id,
                algorithm=algorithm,
                options=options or [],
                deadline=deadline,
            )
            self._proposals[proposal_id] = consensus
            self._stats["total_proposals_created"] += 1
            return consensus

    def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        choice: str,
    ) -> bool:
        """Cast a vote on a consensus proposal.

        Args:
            proposal_id: The proposal identifier.
            voter_id: ID of the voting agent.
            choice: The option being voted for.

        Returns:
            True if the vote was recorded, False otherwise.
        """
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None:
                return False
            if proposal.status not in (ProposalStatus.OPEN, ProposalStatus.VOTING):
                return False
            if voter_id not in self._agents:
                return False
            if proposal.options and choice not in proposal.options:
                return False

            proposal.votes[voter_id] = choice
            if proposal.status == ProposalStatus.OPEN:
                proposal.status = ProposalStatus.VOTING
            return True

    def resolve_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Resolve a consensus proposal using its configured algorithm.

        Args:
            proposal_id: The proposal identifier.

        Returns:
            A dictionary with the resolution result, or None if not found.
        """
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None:
                return None
            if proposal.status not in (ProposalStatus.OPEN, ProposalStatus.VOTING):
                return None

            winner = proposal.resolve()
            tally = proposal.tally_votes()

            if winner is not None:
                if proposal.algorithm == ConsensusAlgorithm.UNANIMOUS:
                    proposal.status = ProposalStatus.PASSED
                elif proposal.algorithm == ConsensusAlgorithm.MAJORITY_VOTE:
                    total = sum(tally.values())
                    if tally.get(winner, 0) > total / 2:
                        proposal.status = ProposalStatus.PASSED
                    else:
                        proposal.status = ProposalStatus.REJECTED
                elif proposal.algorithm == ConsensusAlgorithm.RANKED_CHOICE:
                    total = sum(tally.values())
                    if tally.get(winner, 0) >= total * 0.6:
                        proposal.status = ProposalStatus.PASSED
                    else:
                        proposal.status = ProposalStatus.REJECTED
                else:
                    proposal.status = ProposalStatus.PASSED
            else:
                if tally:
                    top_votes = sorted(tally.values(), reverse=True)
                    if len(top_votes) >= 2 and top_votes[0] == top_votes[1]:
                        proposal.status = ProposalStatus.TIED
                    else:
                        proposal.status = ProposalStatus.REJECTED
                else:
                    proposal.status = ProposalStatus.REJECTED

            result = {
                "proposal_id": proposal_id,
                "algorithm": proposal.algorithm.value,
                "winner": winner,
                "status": proposal.status.value,
                "tally": tally,
                "total_voters": len(proposal.votes),
                "resolved_at": datetime.utcnow().isoformat(),
            }
            proposal.result = result
            self._stats["total_proposals_resolved"] += 1
            return result

    def get_proposal(self, proposal_id: str) -> Optional[ConsensusProposal]:
        """Retrieve a consensus proposal by ID.

        Args:
            proposal_id: The proposal identifier.

        Returns:
            The ConsensusProposal if found, None otherwise.
        """
        with self._lock:
            return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
    ) -> List[ConsensusProposal]:
        """List consensus proposals with optional status filter.

        Args:
            status: Filter by proposal status.

        Returns:
            A filtered list of ConsensusProposals.
        """
        with self._lock:
            proposals = list(self._proposals.values())
            if status:
                proposals = [p for p in proposals if p.status == status]
            return proposals

    # ------------------------------------------------------------------
    # Negotiation
    # ------------------------------------------------------------------

    def start_negotiation(
        self,
        initiator_id: str,
        respondent_id: str,
        topic: str,
    ) -> Negotiation:
        """Start a bilateral negotiation between two agents.

        Args:
            initiator_id: ID of the agent initiating the negotiation.
            respondent_id: ID of the responding agent.
            topic: The subject of negotiation.

        Returns:
            The created Negotiation.

        Raises:
            ValueError: If either agent is not registered.
            RuntimeError: If the maximum negotiation count is exceeded.
        """
        with self._lock:
            if initiator_id not in self._agents:
                raise ValueError(f"Initiator agent '{initiator_id}' is not registered")
            if respondent_id not in self._agents:
                raise ValueError(f"Respondent agent '{respondent_id}' is not registered")

            if len(self._negotiations) >= self.MAX_NEGOTIATIONS:
                raise RuntimeError(
                    f"Maximum negotiation count ({self.MAX_NEGOTIATIONS}) exceeded"
                )

            negotiation_id = uuid.uuid4().hex
            negotiation = Negotiation(
                id=negotiation_id,
                initiator_id=initiator_id,
                respondent_id=respondent_id,
                topic=topic,
            )
            self._negotiations[negotiation_id] = negotiation
            self._stats["total_negotiations_started"] += 1
            return negotiation

    def make_offer(
        self,
        negotiation_id: str,
        agent_id: str,
        offer: Dict[str, Any],
    ) -> bool:
        """Submit an offer in an ongoing negotiation.

        Args:
            negotiation_id: The negotiation identifier.
            agent_id: ID of the agent making the offer.
            offer: The offer details as a dictionary.

        Returns:
            True if the offer was recorded, False otherwise.
        """
        with self._lock:
            negotiation = self._negotiations.get(negotiation_id)
            if negotiation is None:
                return False
            if negotiation.status != NegotiationStatus.ACTIVE:
                return False
            if agent_id not in (negotiation.initiator_id, negotiation.respondent_id):
                return False

            negotiation.add_offer(agent_id, offer)
            return True

    def accept_negotiation(self, negotiation_id: str) -> bool:
        """Accept the current negotiation, finalizing the agreement.

        Args:
            negotiation_id: The negotiation identifier.

        Returns:
            True if the negotiation was accepted, False otherwise.
        """
        with self._lock:
            negotiation = self._negotiations.get(negotiation_id)
            if negotiation is None:
                return False
            if negotiation.status != NegotiationStatus.ACTIVE:
                return False
            if not negotiation.offers:
                return False

            negotiation.phase = NegotiationPhase.ACCEPTANCE
            negotiation.status = NegotiationStatus.ACCEPTED
            negotiation.agreement = {
                "topic": negotiation.topic,
                "initiator_id": negotiation.initiator_id,
                "respondent_id": negotiation.respondent_id,
                "final_offer": negotiation.offers[-1] if negotiation.offers else None,
                "total_offers": len(negotiation.offers),
                "accepted_at": datetime.utcnow().isoformat(),
            }
            self._stats["total_negotiations_resolved"] += 1
            return True

    def reject_negotiation(self, negotiation_id: str) -> bool:
        """Reject the current negotiation.

        Args:
            negotiation_id: The negotiation identifier.

        Returns:
            True if the negotiation was rejected, False otherwise.
        """
        with self._lock:
            negotiation = self._negotiations.get(negotiation_id)
            if negotiation is None:
                return False
            if negotiation.status != NegotiationStatus.ACTIVE:
                return False

            negotiation.phase = NegotiationPhase.REJECTION
            negotiation.status = NegotiationStatus.REJECTED
            self._stats["total_negotiations_resolved"] += 1
            return True

    def cancel_negotiation(self, negotiation_id: str) -> bool:
        """Cancel an active negotiation.

        Args:
            negotiation_id: The negotiation identifier.

        Returns:
            True if the negotiation was cancelled, False otherwise.
        """
        with self._lock:
            negotiation = self._negotiations.get(negotiation_id)
            if negotiation is None:
                return False
            if negotiation.status != NegotiationStatus.ACTIVE:
                return False

            negotiation.status = NegotiationStatus.CANCELLED
            return True

    def get_negotiation(self, negotiation_id: str) -> Optional[Negotiation]:
        """Retrieve a negotiation by ID.

        Args:
            negotiation_id: The negotiation identifier.

        Returns:
            The Negotiation if found, None otherwise.
        """
        with self._lock:
            return self._negotiations.get(negotiation_id)

    def list_negotiations(
        self,
        status: Optional[NegotiationStatus] = None,
    ) -> List[Negotiation]:
        """List negotiations with optional status filter.

        Args:
            status: Filter by negotiation status.

        Returns:
            A filtered list of Negotiations.
        """
        with self._lock:
            negotiations = list(self._negotiations.values())
            if status:
                negotiations = [n for n in negotiations if n.status == status]
            return negotiations

    # ------------------------------------------------------------------
    # Collaboration Sessions
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_type: str,
        participants: Optional[List[str]] = None,
        protocol: ProtocolType = ProtocolType.REQUEST_RESPONSE,
    ) -> CollaborationSession:
        """Create a new collaboration session.

        Args:
            session_type: Human-readable session type description.
            participants: List of agent IDs to include.
            protocol: The communication protocol for the session.

        Returns:
            The created CollaborationSession.

        Raises:
            RuntimeError: If the maximum session count is exceeded.
        """
        with self._lock:
            if len(self._sessions) >= self.MAX_SESSIONS:
                raise RuntimeError(
                    f"Maximum session count ({self.MAX_SESSIONS}) exceeded"
                )

            session_id = uuid.uuid4().hex
            session = CollaborationSession(
                id=session_id,
                session_type=session_type,
                participants=participants or [],
                protocol=protocol,
            )
            self._sessions[session_id] = session
            self._stats["total_sessions_created"] += 1
            return session

    def add_participant_to_session(
        self,
        session_id: str,
        agent_id: str,
    ) -> bool:
        """Add an agent to a collaboration session.

        Args:
            session_id: The session identifier.
            agent_id: The agent to add.

        Returns:
            True if the agent was added, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if agent_id not in self._agents:
                return False
            return session.add_participant(agent_id)

    def remove_participant_from_session(
        self,
        session_id: str,
        agent_id: str,
    ) -> bool:
        """Remove an agent from a collaboration session.

        Args:
            session_id: The session identifier.
            agent_id: The agent to remove.

        Returns:
            True if the agent was removed, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            return session.remove_participant(agent_id)

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Retrieve a collaboration session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The CollaborationSession if found, None otherwise.
        """
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> List[CollaborationSession]:
        """List all collaboration sessions.

        Returns:
            A list of all CollaborationSessions.
        """
        with self._lock:
            return list(self._sessions.values())

    def update_session_state(
        self,
        session_id: str,
        state: SessionState,
    ) -> bool:
        """Update the state of a collaboration session.

        Args:
            session_id: The session identifier.
            state: The new session state.

        Returns:
            True if the session was updated, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.state = state
            session.updated_at = datetime.utcnow().isoformat()
            return True

    # ------------------------------------------------------------------
    # Stats and Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics for the protocol engine.

        Includes aggregate counts for agents, messages, delegations,
        proposals, negotiations, and sessions.
        """
        with self._lock:
            completed_delegations = sum(
                1 for d in self._delegations.values()
                if d.status == DelegationStatus.COMPLETED
            )
            failed_delegations = sum(
                1 for d in self._delegations.values()
                if d.status == DelegationStatus.FAILED
            )
            active_delegations = sum(
                1 for d in self._delegations.values()
                if d.is_active
            )

            resolved_proposals = sum(
                1 for p in self._proposals.values()
                if p.status in (ProposalStatus.PASSED, ProposalStatus.REJECTED)
            )
            passed_proposals = sum(
                1 for p in self._proposals.values()
                if p.status == ProposalStatus.PASSED
            )

            resolved_negotiations = sum(
                1 for n in self._negotiations.values()
                if n.status in (NegotiationStatus.ACCEPTED, NegotiationStatus.REJECTED)
            )
            accepted_negotiations = sum(
                1 for n in self._negotiations.values()
                if n.status == NegotiationStatus.ACCEPTED
            )

            active_sessions = sum(
                1 for s in self._sessions.values()
                if s.state == SessionState.ACTIVE
            )

            role_distribution: Dict[str, int] = {}
            for agent in self._agents.values():
                role_key = agent.role.value
                role_distribution[role_key] = role_distribution.get(role_key, 0) + 1

            return {
                "name": self._name,
                "agents": {
                    "total": len(self._agents),
                    "by_role": role_distribution,
                },
                "messages": {
                    "total": len(self._messages),
                    "history_size": len(self._message_history),
                },
                "delegations": {
                    "total": len(self._delegations),
                    "active": active_delegations,
                    "completed": completed_delegations,
                    "failed": failed_delegations,
                },
                "proposals": {
                    "total": len(self._proposals),
                    "resolved": resolved_proposals,
                    "passed": passed_proposals,
                },
                "negotiations": {
                    "total": len(self._negotiations),
                    "resolved": resolved_negotiations,
                    "accepted": accepted_negotiations,
                },
                "sessions": {
                    "total": len(self._sessions),
                    "active": active_sessions,
                },
                "lifetime": self._stats,
            }

    def reset(self) -> None:
        """Reset all protocol engine state, clearing all data."""
        with self._lock:
            self._agents.clear()
            self._messages.clear()
            self._delegations.clear()
            self._proposals.clear()
            self._negotiations.clear()
            self._sessions.clear()
            self._message_history.clear()
            self._stats = {
                "total_agents_registered": 0,
                "total_agents_unregistered": 0,
                "total_messages_sent": 0,
                "total_delegations_created": 0,
                "total_delegations_completed": 0,
                "total_proposals_created": 0,
                "total_proposals_resolved": 0,
                "total_negotiations_started": 0,
                "total_negotiations_resolved": 0,
                "total_sessions_created": 0,
            }


# ------------------------------------------------------------------
# Module-level singleton accessor
# ------------------------------------------------------------------


def get_multi_agent_protocol(name: str = "default") -> MultiAgentProtocolEngine:
    """Return a named singleton MultiAgentProtocolEngine instance.

    Args:
        name: The instance name (defaults to "default").

    Returns:
        The MultiAgentProtocolEngine singleton for the given name.
    """
    return MultiAgentProtocolEngine.get_instance(name)