"""
SparkLabs Engine - Mail & Message System

An in-game mail and message delivery system for the SparkLabs AI-native
game engine. Manages player-to-player mail with text content, item
attachments, currency transfers, cash-on-delivery (COD) payments,
read/unread tracking, expiration timers, bulk mail for system
announcements, and mail folder organization.

Each mail entry stores sender and recipient IDs, subject and body text,
optional item attachments with quantities, optional currency amounts,
COD pricing for paid deliveries, expiration timestamps, read status,
and folder classification. Designed for MMO mailboxes, reward delivery
systems, and administrative announcements.

Architecture:
  MailSystem (singleton)
    |-- MailFolder, MailPriority, MailEventKind
    |-- MailAttachment, MailEntry, MailTemplate, MailConfig,
       MailStats, MailSnapshot, MailEvent
    |-- get_mail_system

Core Capabilities:
  - send_mail / remove_mail / get_mail / list_mail: manage individual
    mail entries between players.
  - mark_read / mark_unread: control mail read state.
  - claim_attachment / return_mail: handle item attachments and COD.
  - send_bulk_mail: broadcast mail to multiple recipients.
  - register_template / get_template / list_templates: reusable mail
    templates for system announcements.
  - move_to_folder: organize mail into folders.
  - expire_mail: process expired mail and return attachments.
  - tick: advance expiration timers and auto-cleanup.
  - set_config / get_config: global tuning for max mail, expiry, and
    attachment limits.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`MailSystem.get_instance` or the module-level :func:`get_mail_system`
factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_MAIL: int = 50000
_MAX_TEMPLATES: int = 200
_MAX_ATTACHMENTS_PER_MAIL: int = 10
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MailFolder(str, Enum):
    """Folder classification for mail entries."""
    INBOX = "inbox"
    SENT = "sent"
    ARCHIVE = "archive"
    SYSTEM = "system"
    TRASH = "trash"


class MailPriority(str, Enum):
    """Priority level for mail entries."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MailEventKind(str, Enum):
    """Audit event types emitted by the mail system."""
    MAIL_SENT = "mail_sent"
    MAIL_REMOVED = "mail_removed"
    MAIL_READ = "mail_read"
    MAIL_UNREAD = "mail_unread"
    ATTACHMENT_CLAIMED = "attachment_claimed"
    MAIL_RETURNED = "mail_returned"
    BULK_MAIL_SENT = "bulk_mail_sent"
    MAIL_EXPIRED = "mail_expired"
    MAIL_MOVED = "mail_moved"
    TEMPLATE_REGISTERED = "template_registered"
    TEMPLATE_REMOVED = "template_removed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MailAttachment:
    """An item attachment in a mail entry."""
    item_id: str
    item_name: str = ""
    quantity: int = 1
    rarity: str = "common"
    icon: str = ""
    claimed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MailEntry:
    """An individual mail entry between players or system."""
    mail_id: str
    sender_id: str
    recipient_id: str
    subject: str = ""
    body: str = ""
    priority: str = MailPriority.NORMAL.value
    folder: str = MailFolder.INBOX.value
    attachments: List[MailAttachment] = field(default_factory=list)
    currency: int = 0
    currency_type: str = "gold"
    cod_price: int = 0
    cod_paid: bool = False
    read: bool = False
    claimed: bool = False
    returned: bool = False
    expired: bool = False
    send_time: float = field(default_factory=_now)
    expire_time: float = 0.0
    read_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MailTemplate:
    """A reusable mail template for system announcements."""
    template_id: str
    name: str = ""
    subject: str = ""
    body: str = ""
    priority: str = MailPriority.NORMAL.value
    sender_id: str = "system"
    default_expire_days: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MailConfig:
    """Global tuning parameters for the mail system."""
    max_mail: int = 10000
    max_templates: int = 100
    max_attachments_per_mail: int = 5
    default_expire_days: int = 30
    max_expire_days: int = 90
    enable_cod: bool = True
    max_currency_per_mail: int = 1000000
    auto_cleanup_expired: bool = True
    tick_rate_hz: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MailStats:
    """Aggregate statistics for the mail system."""
    total_mail: int = 0
    unread_mail: int = 0
    read_mail: int = 0
    total_sent: int = 0
    total_attachments: int = 0
    attachments_claimed: int = 0
    total_cod: int = 0
    cod_paid: int = 0
    expired_mail: int = 0
    returned_mail: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MailSnapshot:
    """Full state snapshot of the mail system."""
    mail: List[Dict[str, Any]] = field(default_factory=list)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MailEvent:
    """An audit event emitted by the mail system."""
    event_id: str
    kind: str
    timestamp: float
    mail_id: Optional[str] = None
    sender_id: Optional[str] = None
    recipient_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Mail System
# ---------------------------------------------------------------------------

class MailSystem:
    """Manages in-game mail with attachments, COD, and expiration."""

    _instance: Optional["MailSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._mail: Dict[str, MailEntry] = {}
        self._templates: Dict[str, MailTemplate] = {}
        self._events: List[MailEvent] = []
        self._stats = MailStats()
        self._config = MailConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._mail_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "MailSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample mail entries and templates."""
        with self._init_lock:
            if self._initialized:
                return
            self._mail_counter += 1
            mail1 = MailEntry(
                mail_id="mail_starter_01",
                sender_id="system",
                recipient_id="player_starter",
                subject="Welcome to SparkLabs!",
                body="Welcome to the SparkLabs AI-native game engine! Enjoy your adventure.",
                priority=MailPriority.HIGH.value,
                folder=MailFolder.SYSTEM.value,
                attachments=[
                    MailAttachment(item_id="item_starter_pack", item_name="Starter Pack",
                                   quantity=1, rarity="rare", icon="starter_pack_icon"),
                ],
                currency=1000,
                currency_type="gold",
                read=False,
                expire_time=_now() + 30 * 86400,
            )
            self._mail[mail1.mail_id] = mail1

            self._mail_counter += 1
            mail2 = MailEntry(
                mail_id="mail_starter_02",
                sender_id="player_friend_01",
                recipient_id="player_starter",
                subject="Gift for you!",
                body="Found this extra item, thought you might need it.",
                priority=MailPriority.NORMAL.value,
                folder=MailFolder.INBOX.value,
                attachments=[
                    MailAttachment(item_id="item_health_potion", item_name="Health Potion",
                                   quantity=5, rarity="common", icon="potion_icon"),
                ],
                read=True,
                read_time=_now() - 3600,
                expire_time=_now() + 14 * 86400,
            )
            self._mail[mail2.mail_id] = mail2

            self._mail_counter += 1
            mail3 = MailEntry(
                mail_id="mail_starter_03",
                sender_id="merchant_ironforge",
                recipient_id="player_starter",
                subject="Special Offer: Rare Ore",
                body="I have a rare ore shipment. Pay 500 gold to claim it!",
                priority=MailPriority.NORMAL.value,
                folder=MailFolder.INBOX.value,
                attachments=[
                    MailAttachment(item_id="item_rare_ore", item_name="Rare Ore",
                                   quantity=3, rarity="epic", icon="rare_ore_icon"),
                ],
                cod_price=500,
                cod_paid=False,
                read=False,
                expire_time=_now() + 7 * 86400,
            )
            self._mail[mail3.mail_id] = mail3

            template = MailTemplate(
                template_id="tpl_welcome",
                name="Welcome Mail",
                subject="Welcome to the game!",
                body="Thank you for joining. Here are some rewards to get you started!",
                priority=MailPriority.HIGH.value,
                sender_id="system",
                default_expire_days=30,
            )
            self._templates[template.template_id] = template

            self._stats.total_mail = len(self._mail)
            self._stats.unread_mail = sum(1 for m in self._mail.values() if not m.read)
            self._stats.read_mail = sum(1 for m in self._mail.values() if m.read)
            self._stats.total_sent = len(self._mail)
            self._stats.total_attachments = sum(len(m.attachments) for m in self._mail.values())
            self._stats.total_cod = sum(1 for m in self._mail.values() if m.cod_price > 0)
            self._initialized = True

    # ------------------------------------------------------------------
    # Mail Management
    # ------------------------------------------------------------------

    def send_mail(self, mail: MailEntry) -> Dict[str, Any]:
        with self._lock:
            if len(self._mail) >= _MAX_MAIL:
                return {"registered": False, "reason": "capacity_reached"}
            if mail.mail_id in self._mail:
                return {"registered": False, "reason": "mail_exists"}
            if len(mail.attachments) > self._config.max_attachments_per_mail:
                return {"registered": False, "reason": "too_many_attachments"}
            if mail.currency > self._config.max_currency_per_mail:
                return {"registered": False, "reason": "currency_exceeds_limit"}
            if mail.cod_price > 0 and not self._config.enable_cod:
                return {"registered": False, "reason": "cod_disabled"}
            if mail.expire_time == 0:
                mail.expire_time = _now() + self._config.default_expire_days * 86400
            self._mail[mail.mail_id] = mail
            self._stats.total_mail = len(self._mail)
            self._stats.unread_mail += 1 if not mail.read else 0
            self._stats.total_sent += 1
            self._stats.total_attachments += len(mail.attachments)
            if mail.cod_price > 0:
                self._stats.total_cod += 1
            self._emit_event(MailEventKind.MAIL_SENT.value, mail_id=mail.mail_id,
                             sender_id=mail.sender_id, recipient_id=mail.recipient_id)
            return {"registered": True, "mail_id": mail.mail_id}

    def remove_mail(self, mail_id: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"removed": False, "reason": "mail_not_found"}
            if not mail.read:
                self._stats.unread_mail = max(0, self._stats.unread_mail - 1)
            else:
                self._stats.read_mail = max(0, self._stats.read_mail - 1)
            del self._mail[mail_id]
            self._stats.total_mail = len(self._mail)
            self._emit_event(MailEventKind.MAIL_REMOVED.value, mail_id=mail_id)
            return {"removed": True, "mail_id": mail_id}

    def get_mail(self, mail_id: str) -> Optional[MailEntry]:
        with self._lock:
            return self._mail.get(mail_id)

    def list_mail(self, recipient_id: Optional[str] = None, sender_id: Optional[str] = None,
                  folder: Optional[str] = None, unread: Optional[bool] = None,
                  limit: int = 100) -> List[MailEntry]:
        with self._lock:
            result = []
            for m in self._mail.values():
                if recipient_id and m.recipient_id != recipient_id:
                    continue
                if sender_id and m.sender_id != sender_id:
                    continue
                if folder and m.folder != folder:
                    continue
                if unread is not None and m.read == unread:
                    continue
                result.append(m)
            return result[:limit]

    # ------------------------------------------------------------------
    # Read State
    # ------------------------------------------------------------------

    def mark_read(self, mail_id: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"success": False, "reason": "mail_not_found"}
            if not mail.read:
                mail.read = True
                mail.read_time = _now()
                self._stats.unread_mail = max(0, self._stats.unread_mail - 1)
                self._stats.read_mail += 1
                self._emit_event(MailEventKind.MAIL_READ.value, mail_id=mail_id)
            return {"success": True, "mail_id": mail_id, "read": True}

    def mark_unread(self, mail_id: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"success": False, "reason": "mail_not_found"}
            if mail.read:
                mail.read = False
                mail.read_time = 0.0
                self._stats.unread_mail += 1
                self._stats.read_mail = max(0, self._stats.read_mail - 1)
                self._emit_event(MailEventKind.MAIL_UNREAD.value, mail_id=mail_id)
            return {"success": True, "mail_id": mail_id, "read": False}

    # ------------------------------------------------------------------
    # Attachments & COD
    # ------------------------------------------------------------------

    def claim_attachment(self, mail_id: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"success": False, "reason": "mail_not_found"}
            if mail.claimed:
                return {"success": False, "reason": "already_claimed"}
            if mail.cod_price > 0 and not mail.cod_paid:
                return {"success": False, "reason": "cod_not_paid"}
            unclaimed = [a for a in mail.attachments if not a.claimed]
            if not unclaimed:
                return {"success": False, "reason": "no_attachments"}
            for a in unclaimed:
                a.claimed = True
            mail.claimed = True
            self._stats.attachments_claimed += len(unclaimed)
            self._emit_event(MailEventKind.ATTACHMENT_CLAIMED.value, mail_id=mail_id,
                             details={"items_claimed": len(unclaimed)})
            return {"success": True, "mail_id": mail_id,
                    "items_claimed": [a.item_id for a in unclaimed],
                    "currency": mail.currency}

    def pay_cod(self, mail_id: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"success": False, "reason": "mail_not_found"}
            if mail.cod_price <= 0:
                return {"success": False, "reason": "no_cod"}
            if mail.cod_paid:
                return {"success": False, "reason": "cod_already_paid"}
            mail.cod_paid = True
            self._stats.cod_paid += 1
            self._emit_event(MailEventKind.ATTACHMENT_CLAIMED.value, mail_id=mail_id,
                             details={"cod_paid": mail.cod_price})
            return {"success": True, "mail_id": mail_id, "cod_paid": mail.cod_price}

    def return_mail(self, mail_id: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"success": False, "reason": "mail_not_found"}
            if mail.returned:
                return {"success": False, "reason": "already_returned"}
            if mail.claimed:
                return {"success": False, "reason": "already_claimed"}
            mail.returned = True
            mail.folder = MailFolder.TRASH.value
            self._stats.returned_mail += 1
            self._emit_event(MailEventKind.MAIL_RETURNED.value, mail_id=mail_id,
                             sender_id=mail.sender_id, recipient_id=mail.recipient_id)
            return {"success": True, "mail_id": mail_id, "returned": True}

    # ------------------------------------------------------------------
    # Bulk Mail
    # ------------------------------------------------------------------

    def send_bulk_mail(self, sender_id: str, recipient_ids: List[str], subject: str,
                       body: str, priority: str = MailPriority.NORMAL.value,
                       attachments: Optional[List[Dict[str, Any]]] = None,
                       currency: int = 0, expire_days: int = 30) -> Dict[str, Any]:
        with self._lock:
            sent_ids = []
            for rid in recipient_ids:
                self._mail_counter += 1
                mail_id = f"mail_bulk_{self._mail_counter}"
                mail_attachments = [MailAttachment(**a) for a in (attachments or [])]
                expire_time = _now() + expire_days * 86400
                mail = MailEntry(
                    mail_id=mail_id,
                    sender_id=sender_id,
                    recipient_id=rid,
                    subject=subject,
                    body=body,
                    priority=priority,
                    folder=MailFolder.SYSTEM.value,
                    attachments=mail_attachments,
                    currency=currency,
                    expire_time=expire_time,
                )
                self._mail[mail_id] = mail
                sent_ids.append(mail_id)
            self._stats.total_mail = len(self._mail)
            self._stats.total_sent += len(sent_ids)
            self._stats.total_attachments += len(attachments or []) * len(recipient_ids)
            self._emit_event(MailEventKind.BULK_MAIL_SENT.value,
                             sender_id=sender_id,
                             details={"count": len(sent_ids), "subject": subject})
            return {"success": True, "sent_count": len(sent_ids), "mail_ids": sent_ids}

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def register_template(self, template: MailTemplate) -> Dict[str, Any]:
        with self._lock:
            if len(self._templates) >= _MAX_TEMPLATES:
                return {"registered": False, "reason": "capacity_reached"}
            if template.template_id in self._templates:
                return {"registered": False, "reason": "template_exists"}
            self._templates[template.template_id] = template
            self._emit_event(MailEventKind.TEMPLATE_REGISTERED.value,
                             details={"template_id": template.template_id})
            return {"registered": True, "template_id": template.template_id}

    def remove_template(self, template_id: str) -> Dict[str, Any]:
        with self._lock:
            if template_id not in self._templates:
                return {"removed": False, "reason": "template_not_found"}
            del self._templates[template_id]
            self._emit_event(MailEventKind.TEMPLATE_REMOVED.value,
                             details={"template_id": template_id})
            return {"removed": True, "template_id": template_id}

    def get_template(self, template_id: str) -> Optional[MailTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(self, limit: int = 100) -> List[MailTemplate]:
        with self._lock:
            return list(self._templates.values())[:limit]

    # ------------------------------------------------------------------
    # Folder Management
    # ------------------------------------------------------------------

    def move_to_folder(self, mail_id: str, folder: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"success": False, "reason": "mail_not_found"}
            old_folder = mail.folder
            mail.folder = folder
            self._emit_event(MailEventKind.MAIL_MOVED.value, mail_id=mail_id,
                             details={"old_folder": old_folder, "new_folder": folder})
            return {"success": True, "mail_id": mail_id, "old_folder": old_folder,
                    "new_folder": folder}

    # ------------------------------------------------------------------
    # Expiration
    # ------------------------------------------------------------------

    def expire_mail(self, mail_id: str) -> Dict[str, Any]:
        with self._lock:
            mail = self._mail.get(mail_id)
            if mail is None:
                return {"success": False, "reason": "mail_not_found"}
            if mail.expired:
                return {"success": False, "reason": "already_expired"}
            mail.expired = True
            mail.folder = MailFolder.TRASH.value
            self._stats.expired_mail += 1
            self._emit_event(MailEventKind.MAIL_EXPIRED.value, mail_id=mail_id)
            return {"success": True, "mail_id": mail_id, "expired": True}

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        with self._lock:
            self._tick_count += 1
            now = _now()
            expired_count = 0
            if self._config.auto_cleanup_expired:
                to_expire = []
                for mail in self._mail.values():
                    if not mail.expired and mail.expire_time > 0 and mail.expire_time < now:
                        to_expire.append(mail.mail_id)
                for mid in to_expire:
                    result = self.expire_mail(mid)
                    if result.get("success"):
                        expired_count += 1
            self._stats.tick_count = self._tick_count
            self._emit_event(MailEventKind.TICK.value,
                             details={"delta_time": delta_time, "expired": expired_count})
            return {"tick_count": self._tick_count, "expired_count": expired_count}

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def get_config(self) -> MailConfig:
        with self._lock:
            return self._config

    def set_config(self, config: MailConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(MailEventKind.CONFIG_UPDATED.value)
            return {"success": True}

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, mail_id: Optional[str] = None,
                    sender_id: Optional[str] = None, recipient_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        self._event_counter += 1
        event = MailEvent(
            event_id=f"me_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            mail_id=mail_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, mail_id: Optional[str] = None, sender_id: Optional[str] = None,
                    limit: int = 100) -> List[MailEvent]:
        with self._lock:
            result = []
            for e in self._events:
                if mail_id and e.mail_id != mail_id:
                    continue
                if sender_id and e.sender_id != sender_id:
                    continue
                result.append(e)
            return result[:limit]

    def get_stats(self) -> MailStats:
        with self._lock:
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_mail": len(self._mail),
                "unread_mail": sum(1 for m in self._mail.values() if not m.read),
                "total_templates": len(self._templates),
                "total_attachments": sum(len(m.attachments) for m in self._mail.values()),
                "total_cod": sum(1 for m in self._mail.values() if m.cod_price > 0),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> MailSnapshot:
        with self._lock:
            return MailSnapshot(
                mail=[m.to_dict() for m in self._mail.values()],
                templates=[t.to_dict() for t in self._templates.values()],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._mail.clear()
            self._templates.clear()
            self._events.clear()
            self._stats = MailStats()
            self._config = MailConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._mail_counter = 0
            self._initialized = False
            self._emit_event(MailEventKind.RESET.value)
            self._seed()
            return {"success": True, "reset": True}


def get_mail_system() -> MailSystem:
    """Factory function for the MailSystem singleton."""
    return MailSystem.get_instance()
