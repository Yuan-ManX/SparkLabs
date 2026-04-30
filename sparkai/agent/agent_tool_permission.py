"""
SparkAI Agent - Tool Permission System

Role-based tool access control that restricts which tools
each agent role can execute. Directors get full access,
workers get restricted toolsets, and specialists get
domain-specific tools.

Architecture:
  ToolPermissionSystem
    |-- PermissionPolicy (role-based access rules)
    |-- ToolClassifier (danger level classification)
    |-- ApprovalGate (human approval for dangerous operations)
    |-- PermissionAuditLog (access tracking)

Permission Hierarchy:
  FULL_ACCESS > WORKSPACE_WRITE > READ_ONLY > RESTRICTED

Role-Tool Mapping:
  DIRECTOR  -> FULL_ACCESS (all tools)
  LEAD      -> WORKSPACE_WRITE (domain tools + write)
  SPECIALIST -> READ_ONLY (domain tools only)
  WORKER    -> RESTRICTED (minimal toolset)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class PermissionLevel(Enum):
    FULL_ACCESS = "full_access"
    WORKSPACE_WRITE = "workspace_write"
    READ_ONLY = "read_only"
    RESTRICTED = "restricted"


class ToolDangerLevel(Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"
    DESTRUCTIVE = "destructive"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class EnforcementResult(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass
class ToolPermission:
    tool_name: str = ""
    required_level: PermissionLevel = PermissionLevel.READ_ONLY
    danger_level: ToolDangerLevel = ToolDangerLevel.SAFE
    description: str = ""
    requires_approval: bool = False
    approval_timeout_seconds: float = 300.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "required_level": self.required_level.value,
            "danger_level": self.danger_level.value,
            "description": self.description,
            "requires_approval": self.requires_approval,
        }


@dataclass
class ApprovalRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    tool_name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    danger_level: ToolDangerLevel = ToolDangerLevel.MODERATE
    reason: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "params": self.params,
            "danger_level": self.danger_level.value,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
        }


@dataclass
class PermissionAuditEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_role: str = ""
    tool_name: str = ""
    result: EnforcementResult = EnforcementResult.ALLOWED
    required_level: PermissionLevel = PermissionLevel.READ_ONLY
    agent_level: PermissionLevel = PermissionLevel.RESTRICTED
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "tool_name": self.tool_name,
            "result": self.result.value,
            "required_level": self.required_level.value,
            "agent_level": self.agent_level.value,
            "timestamp": self.timestamp,
        }


class ToolClassifier:
    """
    Classifies tools by danger level based on their name
    and expected behavior. Destructive tools require explicit
    approval regardless of role permission level.
    """

    DANGER_PATTERNS: Dict[ToolDangerLevel, List[str]] = {
        ToolDangerLevel.DESTRUCTIVE: [
            "delete", "remove", "destroy", "purge", "drop",
            "reset", "wipe", "clear_all", "shutdown",
        ],
        ToolDangerLevel.DANGEROUS: [
            "write", "create", "update", "modify", "execute",
            "deploy", "publish", "compose", "forge",
        ],
        ToolDangerLevel.MODERATE: [
            "send", "dispatch", "delegate", "assign",
            "approve", "reject", "evolve",
        ],
        ToolDangerLevel.SAFE: [
            "read", "get", "list", "search", "find",
            "check", "validate", "stats", "history",
        ],
    }

    def classify(self, tool_name: str) -> ToolDangerLevel:
        name_lower = tool_name.lower()
        for level, patterns in self.DANGER_PATTERNS.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return level
        return ToolDangerLevel.MODERATE


class PermissionPolicy:
    """
    Maps agent roles to permission levels and manages
    the tool permission registry.
    """

    ROLE_LEVELS: Dict[str, PermissionLevel] = {
        "director": PermissionLevel.FULL_ACCESS,
        "lead": PermissionLevel.WORKSPACE_WRITE,
        "specialist": PermissionLevel.READ_ONLY,
        "worker": PermissionLevel.RESTRICTED,
    }

    LEVEL_HIERARCHY: Dict[PermissionLevel, int] = {
        PermissionLevel.FULL_ACCESS: 4,
        PermissionLevel.WORKSPACE_WRITE: 3,
        PermissionLevel.READ_ONLY: 2,
        PermissionLevel.RESTRICTED: 1,
    }

    def __init__(self):
        self._tool_permissions: Dict[str, ToolPermission] = {}
        self._role_overrides: Dict[str, Set[str]] = {}
        self._classifier = ToolClassifier()
        self._seed_permissions()

    def _seed_permissions(self) -> None:
        safe_tools = [
            "get_agent", "list_agents", "get_status", "check_health",
            "list_skills", "list_toolsets", "get_stats", "get_history",
            "search_memory", "recall", "find_template", "find_fixes",
            "list_templates", "list_commands", "list_sessions",
        ]
        moderate_tools = [
            "think", "observe", "reflect", "verify",
            "send_message", "dispatch_task", "assign_task",
            "decompose_task", "propose_consensus",
        ]
        dangerous_tools = [
            "act", "execute_tool", "create_agent", "register_agent",
            "write_file", "create_session", "forge_skill",
            "create_blueprint", "execute_workflow", "compose_skill",
        ]
        destructive_tools = [
            "delete_agent", "remove_agent", "shutdown",
            "reset", "clear_cache", "clear_history",
            "delete_blueprint", "unregister_agent",
        ]

        for tool in safe_tools:
            self._tool_permissions[tool] = ToolPermission(
                tool_name=tool,
                required_level=PermissionLevel.RESTRICTED,
                danger_level=ToolDangerLevel.SAFE,
            )
        for tool in moderate_tools:
            self._tool_permissions[tool] = ToolPermission(
                tool_name=tool,
                required_level=PermissionLevel.READ_ONLY,
                danger_level=ToolDangerLevel.MODERATE,
            )
        for tool in dangerous_tools:
            self._tool_permissions[tool] = ToolPermission(
                tool_name=tool,
                required_level=PermissionLevel.WORKSPACE_WRITE,
                danger_level=ToolDangerLevel.DANGEROUS,
            )
        for tool in destructive_tools:
            self._tool_permissions[tool] = ToolPermission(
                tool_name=tool,
                required_level=PermissionLevel.FULL_ACCESS,
                danger_level=ToolDangerLevel.DESTRUCTIVE,
                requires_approval=True,
            )

    def get_role_level(self, role: str) -> PermissionLevel:
        return self.ROLE_LEVELS.get(role.lower(), PermissionLevel.RESTRICTED)

    def check_permission(self, role: str, tool_name: str) -> EnforcementResult:
        role_level = self.get_role_level(role)

        override_tools = self._role_overrides.get(role.lower(), set())
        if tool_name in override_tools:
            return EnforcementResult.ALLOWED

        perm = self._tool_permissions.get(tool_name)
        if not perm:
            classified_danger = self._classifier.classify(tool_name)
            if classified_danger == ToolDangerLevel.DESTRUCTIVE:
                return EnforcementResult.REQUIRES_APPROVAL
            if classified_danger == ToolDangerLevel.DANGEROUS:
                required = PermissionLevel.WORKSPACE_WRITE
            elif classified_danger == ToolDangerLevel.MODERATE:
                required = PermissionLevel.READ_ONLY
            else:
                required = PermissionLevel.RESTRICTED
        else:
            required = perm.required_level
            if perm.requires_approval and perm.danger_level == ToolDangerLevel.DESTRUCTIVE:
                if role_level.value != PermissionLevel.FULL_ACCESS.value:
                    return EnforcementResult.REQUIRES_APPROVAL

        if self.LEVEL_HIERARCHY.get(role_level, 0) >= self.LEVEL_HIERARCHY.get(required, 0):
            return EnforcementResult.ALLOWED

        return EnforcementResult.DENIED

    def grant_override(self, role: str, tool_name: str) -> None:
        self._role_overrides.setdefault(role.lower(), set()).add(tool_name)

    def revoke_override(self, role: str, tool_name: str) -> None:
        if role.lower() in self._role_overrides:
            self._role_overrides[role.lower()].discard(tool_name)

    def register_tool(self, permission: ToolPermission) -> None:
        self._tool_permissions[permission.tool_name] = permission


class ToolPermissionSystem:
    """
    Unified tool permission system that enforces role-based
    access control, manages approval gates for dangerous
    operations, and tracks all permission checks in an audit log.

    Usage:
        system = ToolPermissionSystem()
        result = system.check("specialist", "execute_tool")
        # result = EnforcementResult.DENIED

        result = system.check("director", "delete_agent")
        # result = EnforcementResult.REQUIRES_APPROVAL
    """

    def __init__(self):
        self._policy = PermissionPolicy()
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._audit_log: List[PermissionAuditEntry] = []
        self._approval_timeout: float = 300.0

    def check(self, agent_role: str, tool_name: str, agent_id: str = "") -> EnforcementResult:
        result = self._policy.check_permission(agent_role, tool_name)

        entry = PermissionAuditEntry(
            agent_id=agent_id,
            agent_role=agent_role,
            tool_name=tool_name,
            result=result,
            agent_level=self._policy.get_role_level(agent_role),
        )
        self._audit_log.append(entry)

        return result

    def request_approval(self, agent_id: str, agent_role: str, tool_name: str, params: Optional[Dict[str, Any]] = None, reason: str = "") -> ApprovalRequest:
        danger = self._policy._classifier.classify(tool_name)
        request = ApprovalRequest(
            agent_id=agent_id,
            tool_name=tool_name,
            params=params or {},
            danger_level=danger,
            reason=reason,
        )
        self._pending_approvals[request.id] = request
        return request

    def approve(self, approval_id: str, approved_by: str = "") -> bool:
        request = self._pending_approvals.get(approval_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        if time.time() - request.created_at > self._approval_timeout:
            request.status = ApprovalStatus.EXPIRED
            return False

        request.status = ApprovalStatus.APPROVED
        request.resolved_at = time.time()
        request.resolved_by = approved_by
        return True

    def deny(self, approval_id: str, denied_by: str = "") -> bool:
        request = self._pending_approvals.get(approval_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.DENIED
        request.resolved_at = time.time()
        request.resolved_by = denied_by
        return True

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._pending_approvals.values() if r.status == ApprovalStatus.PENDING]

    def get_role_tools(self, role: str) -> Dict[str, Any]:
        level = self._policy.get_role_level(role)
        allowed = []
        denied = []
        requires_approval = []

        for tool_name, perm in self._policy._tool_permissions.items():
            result = self._policy.check_permission(role, tool_name)
            if result == EnforcementResult.ALLOWED:
                allowed.append(tool_name)
            elif result == EnforcementResult.REQUIRES_APPROVAL:
                requires_approval.append(tool_name)
            else:
                denied.append(tool_name)

        return {
            "role": role,
            "permission_level": level.value,
            "allowed_tools": allowed,
            "denied_tools": denied,
            "requires_approval": requires_approval,
        }

    def grant_override(self, role: str, tool_name: str) -> None:
        self._policy.grant_override(role, tool_name)

    def revoke_override(self, role: str, tool_name: str) -> None:
        self._policy.revoke_override(role, tool_name)

    def register_tool(self, tool_name: str, required_level: str = "read_only", danger_level: str = "moderate", requires_approval: bool = False) -> ToolPermission:
        perm = ToolPermission(
            tool_name=tool_name,
            required_level=PermissionLevel(required_level),
            danger_level=ToolDangerLevel(danger_level),
            requires_approval=requires_approval,
        )
        self._policy.register_tool(perm)
        return perm

    def get_audit_log(self, limit: int = 100, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        entries = self._audit_log
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        return [e.to_dict() for e in entries[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total_checks = len(self._audit_log)
        allowed = sum(1 for e in self._audit_log if e.result == EnforcementResult.ALLOWED)
        denied = sum(1 for e in self._audit_log if e.result == EnforcementResult.DENIED)
        requires_approval = sum(1 for e in self._audit_log if e.result == EnforcementResult.REQUIRES_APPROVAL)
        pending = sum(1 for r in self._pending_approvals.values() if r.status == ApprovalStatus.PENDING)

        return {
            "total_checks": total_checks,
            "allowed": allowed,
            "denied": denied,
            "requires_approval": requires_approval,
            "pending_approvals": pending,
            "registered_tools": len(self._policy._tool_permissions),
            "role_overrides": {role: list(tools) for role, tools in self._policy._role_overrides.items()},
        }


_global_permission_system: Optional[ToolPermissionSystem] = None


def get_tool_permission_system() -> ToolPermissionSystem:
    global _global_permission_system
    if _global_permission_system is None:
        _global_permission_system = ToolPermissionSystem()
    return _global_permission_system
