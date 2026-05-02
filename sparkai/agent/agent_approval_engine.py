"""
SparkLabs Agent - Approval Engine

Action gate system that controls agent execution of potentially destructive
operations. Provides trust-tier escalation from auto-approve through manual
review to unconditional block. Tracks per-session approval state and
integrates with the recovery engine for automatic escalation.

Architecture:
  ApprovalEngine
    |-- TrustTier (AUTO, LOW, MEDIUM, HIGH, CRITICAL, BLOCKED)
    |-- ApprovalSession (per-session grant tracking)
    |-- ActionClassifier (maps agent actions to trust tiers)
    |-- GrantCache (time-limited session approvals)
    |-- EscalationChain (automatic tier escalation on failure)

Trust Tiers:
  - AUTO: safe operations auto-approved (read, query, status)
  - LOW: low-risk mutations with auto-approve (create entity, add component)
  - MEDIUM: state mutations requiring session grant (modify world, spawn entity)
  - HIGH: destructive operations requiring explicit user approval (delete world, clear scene)
  - CRITICAL: engine-level operations requiring elevated approval (reinitialize engine, reset all)
  - BLOCKED: unconditionally blocked operations (direct file system access, credential exposure)

Usage:
    engine = ApprovalEngine()
    result = engine.request_approval("delete_world", context={"world_id": "abc"})
    if result["approved"]:
        perform_action()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from sparkai.agent.events import EventBus, Event, EventChannel, get_event_bus


class TrustTier(Enum):
    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"


class ApprovalOutcome(Enum):
    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"
    ESCALATED = "escalated"
    TIMEOUT = "timeout"


@dataclass
class ApprovalGrant:
    action: str = ""
    tier: TrustTier = TrustTier.AUTO
    granted_at: float = 0.0
    expires_at: float = 0.0
    max_uses: int = 1
    use_count: int = 0
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def expired(self) -> bool:
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at

    @property
    def exhausted(self) -> bool:
        return self.max_uses > 0 and self.use_count >= self.max_uses


class ApprovalEngine:
    """
    Action gate with trust-tier escalation for agent operations.

    Classifies agent actions into trust tiers and gates execution
    based on session approval state and tier configuration.
    Supports time-limited grants, use-counted approvals, and
    automatic escalation on repeated failures.

    Usage:
        engine = ApprovalEngine()
        engine.configure_tier(TrustTier.HIGH, auto_deny=False, require_user=True)

        result = engine.request_approval("delete_world", level="high")
        if result.approved:
            perform_action()

        engine.grant("delete_world", session_id="s1", max_uses=5, ttl=300)
    """

    # Action patterns mapped to trust tiers
    ACTION_TIER_MAP: Dict[str, TrustTier] = {
        "read": TrustTier.AUTO, "query": TrustTier.AUTO,
        "get": TrustTier.AUTO, "list": TrustTier.AUTO,
        "status": TrustTier.AUTO, "stats": TrustTier.AUTO,
        "create_entity": TrustTier.LOW, "add_component": TrustTier.LOW,
        "spawn": TrustTier.LOW, "create": TrustTier.LOW,
        "set_property": TrustTier.LOW, "add_tag": TrustTier.LOW,
        "modify_world": TrustTier.MEDIUM, "update_system": TrustTier.MEDIUM,
        "change_scene": TrustTier.MEDIUM, "run_pipeline": TrustTier.MEDIUM,
        "delegate_task": TrustTier.MEDIUM, "generate_game": TrustTier.MEDIUM,
        "delete_entity": TrustTier.HIGH, "remove_component": TrustTier.HIGH,
        "delete_world": TrustTier.HIGH, "clear_scene": TrustTier.HIGH,
        "delete_scene": TrustTier.HIGH, "remove_agent": TrustTier.HIGH,
        "reinitialize": TrustTier.CRITICAL, "reset_all": TrustTier.CRITICAL,
        "shutdown": TrustTier.CRITICAL, "destroy": TrustTier.CRITICAL,
        "file_access": TrustTier.BLOCKED, "credential": TrustTier.BLOCKED,
        "system_call": TrustTier.BLOCKED, "network_bind": TrustTier.BLOCKED,
    }

    def __init__(self):
        self._session_grants: Dict[str, Dict[str, ApprovalGrant]] = {}
        self._permanent_grants: Dict[str, ApprovalGrant] = {}
        self._escalation_counts: Dict[str, int] = {}
        self._total_requests: int = 0
        self._total_approved: int = 0
        self._total_denied: int = 0
        self._total_escalated: int = 0
        self._pending_queue: List[Dict[str, Any]] = []
        self._event_bus: Optional[EventBus] = None
        self._auto_deny_tiers: set[TrustTier] = {TrustTier.BLOCKED}
        self._require_user_tiers: set[TrustTier] = {
            TrustTier.CRITICAL, TrustTier.HIGH,
        }
        self._grant_ttl: Dict[TrustTier, float] = {
            TrustTier.LOW: 60.0,
            TrustTier.MEDIUM: 300.0,
            TrustTier.HIGH: 600.0,
            TrustTier.CRITICAL: 1800.0,
        }

    def configure_tier(
        self,
        tier: TrustTier,
        auto_deny: bool = False,
        require_user: bool = False,
        grant_ttl: Optional[float] = None,
    ) -> None:
        if auto_deny:
            self._auto_deny_tiers.add(tier)
        else:
            self._auto_deny_tiers.discard(tier)
        if require_user:
            self._require_user_tiers.add(tier)
        else:
            self._require_user_tiers.discard(tier)
        if grant_ttl is not None:
            self._grant_ttl[tier] = grant_ttl

    def classify_action(self, action: str) -> TrustTier:
        action_lower = action.lower()
        for pattern, tier in self.ACTION_TIER_MAP.items():
            if pattern in action_lower:
                return tier
        return TrustTier.MEDIUM

    def request_approval(
        self,
        action: str,
        level: str = "medium",
        session_id: str = "default",
        context: Optional[Dict[str, Any]] = None,
        auto_grant: bool = False,
    ) -> Dict[str, Any]:
        self._total_requests += 1
        context = context or {}

        tier = self._level_to_tier(level)

        if tier in self._auto_deny_tiers:
            self._total_denied += 1
            return self._deny_result(
                action, tier, f"Action '{action}' is unconditionally blocked",
            )

        if tier == TrustTier.AUTO or (tier == TrustTier.LOW and auto_grant):
            grant = self._create_grant(action, tier, session_id, context, max_uses=1)
            self._apply_grant(session_id, grant)
            self._total_approved += 1
            return self._approve_result(action, tier, "Auto-approved (safe operation)")

        existing = self._check_existing_grant(session_id, action)
        if existing:
            self._total_approved += 1
            return self._approve_result(action, tier, "Previously granted for this session")

        if tier in self._require_user_tiers:
            self._pending_queue.append({
                "action": action, "tier": tier.value,
                "session_id": session_id, "context": context,
                "timestamp": time.time(),
            })
            if self._event_bus:
                self._event_bus.emit(Event(
                    channel=EventChannel.AGENT,
                    topic="approval.pending",
                    source="ApprovalEngine",
                    data={"action": action, "tier": tier.value, "session_id": session_id},
                ))
            self._total_escalated += 1
            return {
                "approved": False,
                "outcome": ApprovalOutcome.PENDING.value,
                "action": action,
                "tier": tier.value,
                "message": (
                    f"Action '{action}' requires user approval. "
                    f"Waiting for confirmation."
                ),
                "status": "approval_required",
            }

        grant = self._create_grant(action, tier, session_id, context)
        self._apply_grant(session_id, grant)
        self._total_approved += 1
        return self._approve_result(action, tier, "Auto-granted for session")

    def grant(
        self,
        action: str,
        session_id: str = "default",
        tier: Optional[TrustTier] = None,
        max_uses: int = 1,
        ttl: float = 300.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalGrant:
        tier = tier or self.classify_action(action)
        grant = ApprovalGrant(
            action=action,
            tier=tier,
            granted_at=time.time(),
            expires_at=time.time() + ttl if ttl > 0 else 0.0,
            max_uses=max_uses,
            context=context or {},
        )
        self._apply_grant(session_id, grant)
        if self._event_bus:
            self._event_bus.emit(Event(
                channel=EventChannel.AGENT,
                topic="approval.granted",
                source="ApprovalEngine",
                data={"action": action, "session_id": session_id, "tier": tier.value},
            ))
        return grant

    def deny(self, action: str, session_id: str = "default") -> bool:
        grants = self._session_grants.get(session_id, {})
        if action in grants:
            del grants[action]
            self._escalate_action(action)
            if self._event_bus:
                self._event_bus.emit(Event(
                    channel=EventChannel.AGENT,
                    topic="approval.denied",
                    source="ApprovalEngine",
                    data={"action": action, "session_id": session_id},
                ))
            return True
        return False

    def revoke_session(self, session_id: str) -> int:
        count = len(self._session_grants.pop(session_id, {}))
        if count > 0 and self._event_bus:
            self._event_bus.emit(Event(
                channel=EventChannel.AGENT,
                topic="approval.revoked",
                source="ApprovalEngine",
                data={"session_id": session_id, "grant_count": count},
            ))
        return count

    def resolve_pending(self, action: str, choice: str, resolve_all: bool = False) -> int:
        resolved = 0
        remaining = []
        for entry in self._pending_queue:
            if entry["action"] == action or resolve_all:
                resolved += 1
                if choice == "approve":
                    self.grant(
                        action=entry["action"],
                        session_id=entry.get("session_id", "default"),
                        tier=self._level_to_tier(entry.get("tier", "medium")),
                        context=entry.get("context", {}),
                    )
                else:
                    self.deny(entry["action"], entry.get("session_id", "default"))
            else:
                remaining.append(entry)
        self._pending_queue = remaining
        return resolved

    def get_pending_approvals(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if session_id:
            return [e for e in self._pending_queue if e.get("session_id") == session_id]
        return list(self._pending_queue)

    def has_blocking_approval(self, session_id: str = "default") -> bool:
        return any(
            e.get("session_id") == session_id and
            self._level_to_tier(e.get("tier", "medium")) in self._require_user_tiers
            for e in self._pending_queue
        )

    def get_session_approvals(self, session_id: str = "default") -> List[Dict[str, Any]]:
        grants = self._session_grants.get(session_id, {})
        return [
            {
                "action": action,
                "tier": g.tier.value,
                "granted_at": g.granted_at,
                "expires_at": g.expires_at,
                "remaining_uses": g.max_uses - g.use_count if g.max_uses > 0 else "unlimited",
                "expired": g.expired,
            }
            for action, g in grants.items()
        ]

    def get_approval_for(self, action: str, session_id: str = "default") -> Optional[Dict[str, Any]]:
        grant = self._session_grants.get(session_id, {}).get(action)
        if not grant:
            return None
        return {
            "action": action,
            "tier": grant.tier.value,
            "approved": not grant.expired and not grant.exhausted,
            "granted_at": grant.granted_at,
            "expires_at": grant.expires_at,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self._total_requests,
            "approved": self._total_approved,
            "denied": self._total_denied,
            "escalated": self._total_escalated,
            "pending_count": len(self._pending_queue),
            "session_count": len(self._session_grants),
            "total_grants": sum(len(g) for g in self._session_grants.values()),
            "approval_rate": round(
                self._total_approved / max(self._total_requests, 1) * 100, 1
            ),
        }

    def clear(self) -> None:
        self._session_grants.clear()
        self._permanent_grants.clear()
        self._pending_queue.clear()
        self._escalation_counts.clear()
        self._total_requests = 0
        self._total_approved = 0
        self._total_denied = 0
        self._total_escalated = 0

    def _level_to_tier(self, level: str) -> TrustTier:
        level_lower = level.lower()
        level_map = {
            "auto": TrustTier.AUTO, "trivial": TrustTier.AUTO,
            "low": TrustTier.LOW, "minor": TrustTier.LOW,
            "medium": TrustTier.MEDIUM, "moderate": TrustTier.MEDIUM,
            "high": TrustTier.HIGH, "major": TrustTier.HIGH,
            "critical": TrustTier.CRITICAL, "blocked": TrustTier.BLOCKED,
        }
        return level_map.get(level_lower, TrustTier.MEDIUM)

    def _create_grant(
        self, action: str, tier: TrustTier, session_id: str,
        context: Dict[str, Any], max_uses: int = 1,
    ) -> ApprovalGrant:
        ttl = self._grant_ttl.get(tier, 300.0)
        return ApprovalGrant(
            action=action,
            tier=tier,
            granted_at=time.time(),
            expires_at=time.time() + ttl,
            max_uses=max_uses,
            context=context,
        )

    def _apply_grant(self, session_id: str, grant: ApprovalGrant) -> None:
        self._session_grants.setdefault(session_id, {})[grant.action] = grant

    def _check_existing_grant(self, session_id: str, action: str) -> Optional[ApprovalGrant]:
        grants = self._session_grants.get(session_id, {})
        grant = grants.get(action)
        if not grant:
            return None
        if grant.expired or grant.exhausted:
            del grants[action]
            return None
        grant.use_count += 1
        if grant.exhausted:
            del grants[action]
        return grant

    def _approve_result(
        self, action: str, tier: TrustTier, message: str,
    ) -> Dict[str, Any]:
        return {
            "approved": True,
            "outcome": ApprovalOutcome.APPROVED.value,
            "action": action,
            "tier": tier.value,
            "message": message,
        }

    def _deny_result(
        self, action: str, tier: TrustTier, message: str,
    ) -> Dict[str, Any]:
        return {
            "approved": False,
            "outcome": ApprovalOutcome.DENIED.value,
            "action": action,
            "tier": tier.value,
            "message": message,
        }

    def _escalate_action(self, action: str) -> int:
        count = self._escalation_counts.get(action, 0) + 1
        self._escalation_counts[action] = count
        return count


_global_approval_engine: Optional[ApprovalEngine] = None


def get_approval_engine() -> ApprovalEngine:
    global _global_approval_engine
    if _global_approval_engine is None:
        _global_approval_engine = ApprovalEngine()
    return _global_approval_engine
