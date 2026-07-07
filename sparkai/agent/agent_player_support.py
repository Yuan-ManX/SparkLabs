"""
SparkLabs Agent - AI Player Support Assistant

Provides an AI-powered in-game support system that reads player state,
diagnoses blockers, generates contextual hints, manages support tickets,
conducts support conversations, and escalates to human agents when needed.

Architecture:
  PlayerSupportAssistant (singleton)
    |-- SupportTicket, SupportIssue, SupportHint, SupportConversation,
        SupportMessage, EscalationCase, SatisfactionSurvey,
        PlayerSupportStats, PlayerSupportSnapshot, PlayerSupportEvent
    |-- IssueCategory, TicketStatus, HintType, Priority,
        EscalationReason, SatisfactionLevel, PlayerSupportEventKind

Core Capabilities:
  - register_ticket / update_ticket / get_ticket / list_tickets /
    close_ticket: support ticket lifecycle management.
  - register_issue / update_issue / get_issue / list_issues /
    delete_issue: knowledge base of known issues and solutions.
  - generate_hint: produce contextual hints based on player state
    and issue diagnosis.
  - start_conversation / send_message / get_conversation /
    list_conversations: AI-driven support chat sessions.
  - escalate_ticket / get_escalation / list_escalations: hand off
    to human support with full context.
  - record_satisfaction: collect player feedback after resolution.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PlayerSupportAssistant.get_instance` or the module-level
:func:`get_player_support_assistant` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TICKETS: int = 5000
_MAX_ISSUES: int = 500
_MAX_HINTS: int = 5000
_MAX_CONVERSATIONS: int = 2000
_MAX_ESCALATIONS: int = 500
_MAX_SURVEYS: int = 5000
_MAX_EVENTS: int = 5000
_MAX_MESSAGES_PER_CONVERSATION: int = 100


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class IssueCategory(Enum):
    GAMEPLAY = "gameplay"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    PAYMENT = "payment"
    PROGRESSION = "progression"
    SOCIAL = "social"
    PERFORMANCE = "performance"
    OTHER = "other"


class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_PLAYER = "waiting_player"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class HintType(Enum):
    WALKTHROUGH = "walkthrough"
    TIP = "tip"
    STRATEGY = "strategy"
    CONTROL_HINT = "control_hint"
    RESOURCE_LINK = "resource_link"
    VIDEO_GUIDE = "video_guide"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class EscalationReason(Enum):
    COMPLEX_ISSUE = "complex_issue"
    PLAYER_REQUEST = "player_request"
    AI_UNSURE = "ai_unsure"
    PAYMENT_DISPUTE = "payment_dispute"
    ACCOUNT_SECURITY = "account_security"
    REPEATED_ISSUE = "repeated_issue"
    NEGATIVE_SENTIMENT = "negative_sentiment"


class SatisfactionLevel(Enum):
    VERY_SATISFIED = "very_satisfied"
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    DISSATISFIED = "dissatisfied"
    VERY_DISSATISFIED = "very_dissatisfied"


class PlayerSupportEventKind(Enum):
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    TICKET_CLOSED = "ticket_closed"
    ISSUE_REGISTERED = "issue_registered"
    ISSUE_UPDATED = "issue_updated"
    HINT_GENERATED = "hint_generated"
    CONVERSATION_STARTED = "conversation_started"
    MESSAGE_SENT = "message_sent"
    TICKET_RESOLVED = "ticket_resolved"
    TICKET_ESCALATED = "ticket_escalated"
    SATISFACTION_RECORDED = "satisfaction_recorded"
    ISSUE_DIAGNOSED = "issue_diagnosed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SupportTicket:
    """A player support ticket."""
    ticket_id: str
    player_id: str
    title: str = ""
    description: str = ""
    category: IssueCategory = IssueCategory.OTHER
    priority: Priority = Priority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    assigned_agent: str = "ai_support"
    issue_id: str = ""
    hint_ids: List[str] = field(default_factory=list)
    conversation_id: str = ""
    escalation_id: str = ""
    game_context: Dict[str, Any] = field(default_factory=dict)
    resolution_notes: str = ""
    resolved_at: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SupportIssue:
    """A known issue in the knowledge base."""
    issue_id: str
    title: str
    category: IssueCategory = IssueCategory.OTHER
    description: str = ""
    root_cause: str = ""
    solution_steps: List[str] = field(default_factory=list)
    affected_versions: List[str] = field(default_factory=list)
    workaround: str = ""
    is_resolved: bool = False
    occurrence_count: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SupportHint:
    """A contextual hint generated for a player."""
    hint_id: str
    ticket_id: str
    player_id: str
    hint_type: HintType = HintType.TIP
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    was_helpful: Optional[bool] = None
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SupportMessage:
    """A single message in a support conversation."""
    message_id: str
    conversation_id: str
    sender: str = "ai_support"
    content: str = ""
    is_ai: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SupportConversation:
    """A support conversation between player and AI/human agent."""
    conversation_id: str
    ticket_id: str
    player_id: str
    agent_id: str = "ai_support"
    is_escalated: bool = False
    message_count: int = 0
    sentiment_score: float = 0.0
    status: str = "active"
    messages: List[SupportMessage] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EscalationCase:
    """An escalation to human support."""
    escalation_id: str
    ticket_id: str
    player_id: str
    reason: EscalationReason = EscalationReason.AI_UNSURE
    priority: Priority = Priority.HIGH
    assigned_to: str = ""
    context_summary: str = ""
    ai_attempt_summary: str = ""
    status: str = "pending"
    resolved_at: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SatisfactionSurvey:
    """Player satisfaction feedback after ticket resolution."""
    survey_id: str
    ticket_id: str
    player_id: str
    satisfaction: SatisfactionLevel = SatisfactionLevel.NEUTRAL
    rating: int = 3
    feedback: str = ""
    resolved_first_contact: bool = False
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerSupportStats:
    """Aggregate statistics for the support system."""
    total_tickets: int = 0
    open_tickets: int = 0
    resolved_tickets: int = 0
    escalated_tickets: int = 0
    total_conversations: int = 0
    total_hints: int = 0
    total_issues: int = 0
    avg_resolution_time_hours: float = 0.0
    avg_satisfaction: float = 0.0
    first_contact_resolution_rate: float = 0.0
    escalation_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerSupportSnapshot:
    """Point-in-time snapshot of the support system."""
    tickets: int = 0
    issues: int = 0
    conversations: int = 0
    escalations: int = 0
    hints: int = 0
    surveys: int = 0
    stats: PlayerSupportStats = field(default_factory=PlayerSupportStats)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerSupportEvent:
    """An event in the support system."""
    event_id: str
    kind: PlayerSupportEventKind
    timestamp: str = field(default_factory=_now)
    ticket_id: str = ""
    player_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Player Support Assistant (Singleton)
# ---------------------------------------------------------------------------


class PlayerSupportAssistant:
    """AI-powered player support assistant with ticket management,
    contextual hint generation, conversation handling, and escalation."""

    _instance: Optional["PlayerSupportAssistant"] = None
    _inner_lock = threading.RLock()

    def __new__(cls) -> "PlayerSupportAssistant":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._tickets: Dict[str, SupportTicket] = {}
            self._issues: Dict[str, SupportIssue] = {}
            self._hints: Dict[str, SupportHint] = {}
            self._conversations: Dict[str, SupportConversation] = {}
            self._escalations: Dict[str, EscalationCase] = {}
            self._surveys: Dict[str, SatisfactionSurvey] = {}
            self._events: List[PlayerSupportEvent] = []
            self._initialized = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        issue = SupportIssue(
            issue_id="issue_seed_stuck",
            title="Player stuck at level 3 boss gate",
            category=IssueCategory.GAMEPLAY,
            description="Player cannot find the hidden switch to open the boss gate.",
            root_cause="Level design does not provide enough visual cues.",
            solution_steps=[
                "Look for a glowing torch on the left wall.",
                "Interact with the torch to reveal the hidden switch.",
                "Press the switch to open the gate.",
            ],
            workaround="Use the fast travel system to skip the area.",
            tags=["level_3", "boss_gate", "stuck"],
        )
        self._issues[issue.issue_id] = issue

        ticket = SupportTicket(
            ticket_id="tkt_seed_stuck",
            player_id="player_seed_1",
            title="Cannot progress past level 3 boss",
            description="I am stuck at the boss gate and cannot find a way through.",
            category=IssueCategory.GAMEPLAY,
            priority=Priority.MEDIUM,
            status=TicketStatus.RESOLVED,
            issue_id="issue_seed_stuck",
            game_context={"level": 3, "area": "boss_gate", "playtime_hours": 4.5},
            resolution_notes="Provided walkthrough hint for hidden switch.",
        )
        self._tickets[ticket.ticket_id] = ticket

        survey = SatisfactionSurvey(
            survey_id="srv_seed_1",
            ticket_id="tkt_seed_stuck",
            player_id="player_seed_1",
            satisfaction=SatisfactionLevel.SATISFIED,
            rating=4,
            feedback="The hint was helpful, thanks!",
            resolved_first_contact=True,
        )
        self._surveys[survey.survey_id] = survey

    # ------------------------------------------------------------------
    # Ticket Management
    # ------------------------------------------------------------------

    def register_ticket(
        self,
        player_id: str,
        title: str = "",
        description: str = "",
        category: IssueCategory = IssueCategory.OTHER,
        priority: Priority = Priority.MEDIUM,
        game_context: Optional[Dict[str, Any]] = None,
    ) -> SupportTicket:
        with self._lock:
            ticket = SupportTicket(
                ticket_id=_new_id("tkt"),
                player_id=player_id,
                title=title,
                description=description,
                category=category,
                priority=priority,
                game_context=game_context or {},
            )
            self._tickets[ticket.ticket_id] = ticket
            _evict_fifo_dict(self._tickets, _MAX_TICKETS)
            self._emit(PlayerSupportEventKind.TICKET_CREATED, {
                "ticket_id": ticket.ticket_id, "player_id": player_id,
            })
            return ticket

    def update_ticket(
        self,
        ticket_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[IssueCategory] = None,
        priority: Optional[Priority] = None,
        status: Optional[TicketStatus] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[SupportTicket]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            if title is not None:
                ticket.title = title
            if description is not None:
                ticket.description = description
            if category is not None:
                ticket.category = category
            if priority is not None:
                ticket.priority = priority
            if status is not None:
                ticket.status = status
                if status == TicketStatus.RESOLVED:
                    ticket.resolved_at = _now()
            if resolution_notes is not None:
                ticket.resolution_notes = resolution_notes
            ticket.updated_at = _now()
            self._emit(PlayerSupportEventKind.TICKET_UPDATED, {"ticket_id": ticket_id})
            return ticket

    def get_ticket(self, ticket_id: str) -> Optional[SupportTicket]:
        with self._lock:
            return self._tickets.get(ticket_id)

    def list_tickets(
        self,
        player_id: Optional[str] = None,
        status: Optional[TicketStatus] = None,
        category: Optional[IssueCategory] = None,
        priority: Optional[Priority] = None,
        limit: int = 100,
    ) -> List[SupportTicket]:
        with self._lock:
            items = list(self._tickets.values())
            if player_id:
                items = [t for t in items if t.player_id == player_id]
            if status:
                items = [t for t in items if t.status == status]
            if category:
                items = [t for t in items if t.category == category]
            if priority:
                items = [t for t in items if t.priority == priority]
            return items[:limit]

    def close_ticket(
        self, ticket_id: str, resolution_notes: str = ""
    ) -> Optional[SupportTicket]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            ticket.status = TicketStatus.CLOSED
            ticket.resolution_notes = resolution_notes
            ticket.resolved_at = _now()
            ticket.updated_at = _now()
            self._emit(PlayerSupportEventKind.TICKET_CLOSED, {"ticket_id": ticket_id})
            return ticket

    # ------------------------------------------------------------------
    # Issue Knowledge Base
    # ------------------------------------------------------------------

    def register_issue(
        self,
        title: str,
        category: IssueCategory = IssueCategory.OTHER,
        description: str = "",
        root_cause: str = "",
        solution_steps: Optional[List[str]] = None,
        workaround: str = "",
        tags: Optional[List[str]] = None,
    ) -> SupportIssue:
        with self._lock:
            issue = SupportIssue(
                issue_id=_new_id("issue"),
                title=title,
                category=category,
                description=description,
                root_cause=root_cause,
                solution_steps=solution_steps or [],
                workaround=workaround,
                tags=tags or [],
            )
            self._issues[issue.issue_id] = issue
            _evict_fifo_dict(self._issues, _MAX_ISSUES)
            self._emit(PlayerSupportEventKind.ISSUE_REGISTERED, {
                "issue_id": issue.issue_id,
            })
            return issue

    def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        root_cause: Optional[str] = None,
        workaround: Optional[str] = None,
        is_resolved: Optional[bool] = None,
    ) -> Optional[SupportIssue]:
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                return None
            if title is not None:
                issue.title = title
            if description is not None:
                issue.description = description
            if root_cause is not None:
                issue.root_cause = root_cause
            if workaround is not None:
                issue.workaround = workaround
            if is_resolved is not None:
                issue.is_resolved = is_resolved
            issue.updated_at = _now()
            self._emit(PlayerSupportEventKind.ISSUE_UPDATED, {"issue_id": issue_id})
            return issue

    def get_issue(self, issue_id: str) -> Optional[SupportIssue]:
        with self._lock:
            return self._issues.get(issue_id)

    def list_issues(
        self,
        category: Optional[IssueCategory] = None,
        is_resolved: Optional[bool] = None,
        limit: int = 100,
    ) -> List[SupportIssue]:
        with self._lock:
            items = list(self._issues.values())
            if category:
                items = [i for i in items if i.category == category]
            if is_resolved is not None:
                items = [i for i in items if i.is_resolved == is_resolved]
            return items[:limit]

    def delete_issue(self, issue_id: str) -> bool:
        with self._lock:
            return self._issues.pop(issue_id, None) is not None

    # ------------------------------------------------------------------
    # Hint Generation
    # ------------------------------------------------------------------

    def generate_hint(
        self,
        ticket_id: str,
        player_id: str,
        hint_type: HintType = HintType.TIP,
        content: str = "",
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8,
    ) -> Optional[SupportHint]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            hint = SupportHint(
                hint_id=_new_id("hnt"),
                ticket_id=ticket_id,
                player_id=player_id,
                hint_type=hint_type,
                content=content,
                context=context or {},
                confidence=confidence,
            )
            self._hints[hint.hint_id] = hint
            _evict_fifo_dict(self._hints, _MAX_HINTS)
            ticket.hint_ids.append(hint.hint_id)
            ticket.updated_at = _now()
            self._emit(PlayerSupportEventKind.HINT_GENERATED, {
                "hint_id": hint.hint_id, "ticket_id": ticket_id,
            })
            return hint

    def get_hint(self, hint_id: str) -> Optional[SupportHint]:
        with self._lock:
            return self._hints.get(hint_id)

    def list_hints(
        self, ticket_id: Optional[str] = None, player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SupportHint]:
        with self._lock:
            items = list(self._hints.values())
            if ticket_id:
                items = [h for h in items if h.ticket_id == ticket_id]
            if player_id:
                items = [h for h in items if h.player_id == player_id]
            return items[:limit]

    def mark_hint_helpful(self, hint_id: str, was_helpful: bool) -> Optional[SupportHint]:
        with self._lock:
            hint = self._hints.get(hint_id)
            if hint is None:
                return None
            hint.was_helpful = was_helpful
            return hint

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    def start_conversation(
        self, ticket_id: str, player_id: str, agent_id: str = "ai_support"
    ) -> Optional[SupportConversation]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            conv = SupportConversation(
                conversation_id=_new_id("conv"),
                ticket_id=ticket_id,
                player_id=player_id,
                agent_id=agent_id,
            )
            self._conversations[conv.conversation_id] = conv
            _evict_fifo_dict(self._conversations, _MAX_CONVERSATIONS)
            ticket.conversation_id = conv.conversation_id
            ticket.status = TicketStatus.IN_PROGRESS
            ticket.updated_at = _now()
            self._emit(PlayerSupportEventKind.CONVERSATION_STARTED, {
                "conversation_id": conv.conversation_id, "ticket_id": ticket_id,
            })
            return conv

    def send_message(
        self,
        conversation_id: str,
        sender: str,
        content: str,
        is_ai: bool = True,
    ) -> Optional[SupportMessage]:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if conv is None:
                return None
            msg = SupportMessage(
                message_id=_new_id("msg"),
                conversation_id=conversation_id,
                sender=sender,
                content=content,
                is_ai=is_ai,
            )
            conv.messages.append(msg)
            _evict_fifo_list(conv.messages, _MAX_MESSAGES_PER_CONVERSATION)
            conv.message_count = len(conv.messages)
            conv.updated_at = _now()
            self._emit(PlayerSupportEventKind.MESSAGE_SENT, {
                "message_id": msg.message_id, "conversation_id": conversation_id,
            })
            return msg

    def get_conversation(self, conversation_id: str) -> Optional[SupportConversation]:
        with self._lock:
            return self._conversations.get(conversation_id)

    def list_conversations(
        self, ticket_id: Optional[str] = None, player_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SupportConversation]:
        with self._lock:
            items = list(self._conversations.values())
            if ticket_id:
                items = [c for c in items if c.ticket_id == ticket_id]
            if player_id:
                items = [c for c in items if c.player_id == player_id]
            return items[:limit]

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    def escalate_ticket(
        self,
        ticket_id: str,
        reason: EscalationReason = EscalationReason.AI_UNSURE,
        priority: Priority = Priority.HIGH,
        context_summary: str = "",
        ai_attempt_summary: str = "",
    ) -> Optional[EscalationCase]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            esc = EscalationCase(
                escalation_id=_new_id("esc"),
                ticket_id=ticket_id,
                player_id=ticket.player_id,
                reason=reason,
                priority=priority,
                context_summary=context_summary,
                ai_attempt_summary=ai_attempt_summary,
            )
            self._escalations[esc.escalation_id] = esc
            _evict_fifo_dict(self._escalations, _MAX_ESCALATIONS)
            ticket.escalation_id = esc.escalation_id
            ticket.status = TicketStatus.ESCALATED
            ticket.updated_at = _now()
            self._emit(PlayerSupportEventKind.TICKET_ESCALATED, {
                "escalation_id": esc.escalation_id, "ticket_id": ticket_id,
            })
            return esc

    def get_escalation(self, escalation_id: str) -> Optional[EscalationCase]:
        with self._lock:
            return self._escalations.get(escalation_id)

    def list_escalations(
        self, ticket_id: Optional[str] = None, status: Optional[str] = None,
        limit: int = 50,
    ) -> List[EscalationCase]:
        with self._lock:
            items = list(self._escalations.values())
            if ticket_id:
                items = [e for e in items if e.ticket_id == ticket_id]
            if status:
                items = [e for e in items if e.status == status]
            return items[:limit]

    def resolve_escalation(
        self, escalation_id: str, assigned_to: str = "", resolution: str = ""
    ) -> Optional[EscalationCase]:
        with self._lock:
            esc = self._escalations.get(escalation_id)
            if esc is None:
                return None
            esc.status = "resolved"
            esc.resolved_at = _now()
            esc.updated_at = _now()
            if assigned_to:
                esc.assigned_to = assigned_to
            ticket = self._tickets.get(esc.ticket_id)
            if ticket:
                ticket.status = TicketStatus.RESOLVED
                ticket.resolution_notes = resolution
                ticket.resolved_at = _now()
                ticket.updated_at = _now()
            return esc

    # ------------------------------------------------------------------
    # Satisfaction
    # ------------------------------------------------------------------

    def record_satisfaction(
        self,
        ticket_id: str,
        player_id: str,
        satisfaction: SatisfactionLevel = SatisfactionLevel.NEUTRAL,
        rating: int = 3,
        feedback: str = "",
        resolved_first_contact: bool = False,
    ) -> Optional[SatisfactionSurvey]:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            survey = SatisfactionSurvey(
                survey_id=_new_id("srv"),
                ticket_id=ticket_id,
                player_id=player_id,
                satisfaction=satisfaction,
                rating=max(1, min(5, rating)),
                feedback=feedback,
                resolved_first_contact=resolved_first_contact,
            )
            self._surveys[survey.survey_id] = survey
            _evict_fifo_dict(self._surveys, _MAX_SURVEYS)
            self._emit(PlayerSupportEventKind.SATISFACTION_RECORDED, {
                "survey_id": survey.survey_id, "ticket_id": ticket_id,
            })
            return survey

    def list_surveys(
        self, ticket_id: Optional[str] = None, limit: int = 50
    ) -> List[SatisfactionSurvey]:
        with self._lock:
            items = list(self._surveys.values())
            if ticket_id:
                items = [s for s in items if s.ticket_id == ticket_id]
            return items[:limit]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _emit(self, kind: PlayerSupportEventKind, data: Dict[str, Any]) -> None:
        event = PlayerSupportEvent(
            event_id=_new_id("evt"),
            kind=kind,
            ticket_id=data.get("ticket_id", ""),
            player_id=data.get("player_id", ""),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(
        self, kind: Optional[PlayerSupportEventKind] = None, limit: int = 100
    ) -> List[PlayerSupportEvent]:
        with self._lock:
            items = self._events
            if kind:
                items = [e for e in items if e.kind == kind]
            return list(items[:limit])

    def get_stats(self) -> PlayerSupportStats:
        with self._lock:
            total = len(self._tickets)
            open_count = sum(1 for t in self._tickets.values() if t.status == TicketStatus.OPEN)
            resolved = sum(1 for t in self._tickets.values() if t.status == TicketStatus.RESOLVED)
            escalated = sum(1 for t in self._tickets.values() if t.status == TicketStatus.ESCALATED)
            surveys = list(self._surveys.values())
            avg_sat = 0.0
            if surveys:
                scores = {
                    SatisfactionLevel.VERY_SATISFIED: 5,
                    SatisfactionLevel.SATISFIED: 4,
                    SatisfactionLevel.NEUTRAL: 3,
                    SatisfactionLevel.DISSATISFIED: 2,
                    SatisfactionLevel.VERY_DISSATISFIED: 1,
                }
                avg_sat = sum(scores.get(s.satisfaction, 3) for s in surveys) / len(surveys)
            fcr = 0.0
            if surveys:
                fcr = sum(1 for s in surveys if s.resolved_first_contact) / len(surveys)
            esc_rate = escalated / total if total > 0 else 0.0
            return PlayerSupportStats(
                total_tickets=total,
                open_tickets=open_count,
                resolved_tickets=resolved,
                escalated_tickets=escalated,
                total_conversations=len(self._conversations),
                total_hints=len(self._hints),
                total_issues=len(self._issues),
                avg_satisfaction=round(avg_sat, 2),
                first_contact_resolution_rate=round(fcr, 2),
                escalation_rate=round(esc_rate, 2),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "tickets": len(self._tickets),
                "issues": len(self._issues),
                "hints": len(self._hints),
                "conversations": len(self._conversations),
                "escalations": len(self._escalations),
                "surveys": len(self._surveys),
                "events": len(self._events),
            }

    def get_snapshot(self) -> PlayerSupportSnapshot:
        with self._lock:
            return PlayerSupportSnapshot(
                tickets=len(self._tickets),
                issues=len(self._issues),
                conversations=len(self._conversations),
                escalations=len(self._escalations),
                hints=len(self._hints),
                surveys=len(self._surveys),
                stats=self.get_stats(),
            )

    def reset(self) -> None:
        with self._lock:
            self._tickets.clear()
            self._issues.clear()
            self._hints.clear()
            self._conversations.clear()
            self._escalations.clear()
            self._surveys.clear()
            self._events.clear()
            self._seed_data()


def get_player_support_assistant() -> PlayerSupportAssistant:
    """Get the singleton PlayerSupportAssistant instance."""
    return PlayerSupportAssistant()
