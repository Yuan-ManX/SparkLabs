"""
SparkLabs Validation Hooks System

Pre/post execution validation framework for AI-native game engine operations.
Provides configurable hooks for quality gates, approval workflows, and safety checks.
"""

from __future__ import annotations

import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


class HookPhase(Enum):
    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
    PRE_PLAN = "pre_plan"
    POST_PLAN = "post_plan"
    PRE_STEP = "pre_step"
    POST_STEP = "post_step"
    PRE_DELEGATE = "pre_delegate"
    POST_DELEGATE = "post_delegate"
    ON_ERROR = "on_error"
    ON_TIMEOUT = "on_timeout"


class HookAction(Enum):
    CONTINUE = "continue"
    ABORT = "abort"
    RETRY = "retry"
    SKIP = "skip"
    REQUIRE_APPROVAL = "require_approval"
    MODIFY_PARAMS = "modify_params"


class HookSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HookCondition:
    field: str
    operator: str = "eq"
    value: Any = None
    description: str = ""


@dataclass
class HookRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    phase: HookPhase = HookPhase.PRE_EXECUTE
    severity: HookSeverity = HookSeverity.MEDIUM
    conditions: List[HookCondition] = field(default_factory=list)
    action: HookAction = HookAction.CONTINUE
    max_retries: int = 0
    retry_delay_ms: float = 1000.0
    timeout_ms: float = 30000.0
    enabled: bool = True
    path_scope: Optional[str] = None
    agent_scope: Optional[str] = None
    category: str = "general"


@dataclass
class HookResult:
    rule_id: str = ""
    rule_name: str = ""
    action: HookAction = HookAction.CONTINUE
    passed: bool = True
    message: str = ""
    modified_params: Optional[Dict[str, Any]] = None
    severity: HookSeverity = HookSeverity.LOW
    duration_ms: float = 0.0


@dataclass
class HookExecution:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    phase: HookPhase = HookPhase.PRE_EXECUTE
    rule_id: str = ""
    result: Optional[HookResult] = None
    timestamp: float = field(default_factory=time.time)


class ValidationHooksSystem:
    """
    Unified validation hooks system for SparkLabs game engine.

    Provides configurable pre/post execution hooks that enforce quality standards,
    safety constraints, and approval workflows across all agent operations.
    """

    def __init__(self):
        self._rules: Dict[str, HookRule] = {}
        self._custom_handlers: Dict[str, Callable] = {}
        self._executions: List[HookExecution] = []
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}
        self._max_executions = 1000
        self._seed_rules()

    def _seed_rules(self):
        safety_rules = [
            HookRule(
                name="prevent_unrestricted_code_execution",
                description="Block unrestricted shell command execution without approval",
                phase=HookPhase.PRE_EXECUTE,
                severity=HookSeverity.CRITICAL,
                conditions=[
                    HookCondition(field="tool", operator="eq", value="shell_exec", description="Shell execution tool"),
                    HookCondition(field="params.restricted", operator="eq", value=False, description="Not marked as restricted"),
                ],
                action=HookAction.REQUIRE_APPROVAL,
                category="safety",
            ),
            HookRule(
                name="prevent_asset_deletion_without_approval",
                description="Require approval before deleting game assets",
                phase=HookPhase.PRE_EXECUTE,
                severity=HookSeverity.HIGH,
                conditions=[
                    HookCondition(field="tool", operator="eq", value="asset_delete", description="Asset deletion tool"),
                ],
                action=HookAction.REQUIRE_APPROVAL,
                category="safety",
            ),
            HookRule(
                name="enforce_timeout_on_long_operations",
                description="Enforce timeout limits on operations that may run indefinitely",
                phase=HookPhase.PRE_EXECUTE,
                severity=HookSeverity.MEDIUM,
                conditions=[
                    HookCondition(field="tool", operator="in", value=["code_generate", "asset_generate", "world_build"], description="Long-running tools"),
                ],
                action=HookAction.CONTINUE,
                timeout_ms=120000.0,
                category="safety",
            ),
        ]

        quality_rules = [
            HookRule(
                name="verify_build_after_code_changes",
                description="Run build verification after code generation or modification",
                phase=HookPhase.POST_EXECUTE,
                severity=HookSeverity.HIGH,
                conditions=[
                    HookCondition(field="tool", operator="in", value=["code_generate", "code_modify", "file_write"], description="Code modification tools"),
                ],
                action=HookAction.CONTINUE,
                category="quality",
            ),
            HookRule(
                name="check_asset_integrity_after_generation",
                description="Validate generated assets meet format and size requirements",
                phase=HookPhase.POST_EXECUTE,
                severity=HookSeverity.MEDIUM,
                conditions=[
                    HookCondition(field="tool", operator="in", value=["asset_generate", "texture_generate", "model_generate"], description="Asset generation tools"),
                ],
                action=HookAction.CONTINUE,
                category="quality",
            ),
            HookRule(
                name="validate_scene_consistency",
                description="Ensure scene remains consistent after entity modifications",
                phase=HookPhase.POST_EXECUTE,
                severity=HookSeverity.MEDIUM,
                conditions=[
                    HookCondition(field="tool", operator="in", value=["entity_create", "entity_update", "entity_delete", "scene_modify"], description="Scene modification tools"),
                ],
                action=HookAction.CONTINUE,
                category="quality",
            ),
        ]

        performance_rules = [
            HookRule(
                name="warn_on_slow_execution",
                description="Warn when tool execution exceeds expected duration",
                phase=HookPhase.POST_EXECUTE,
                severity=HookSeverity.LOW,
                conditions=[
                    HookCondition(field="duration_ms", operator="gt", value=10000, description="Execution took more than 10 seconds"),
                ],
                action=HookAction.CONTINUE,
                category="performance",
            ),
            HookRule(
                name="limit_concurrent_operations",
                description="Prevent too many concurrent operations from overwhelming the engine",
                phase=HookPhase.PRE_EXECUTE,
                severity=HookSeverity.MEDIUM,
                conditions=[
                    HookCondition(field="concurrent_count", operator="gt", value=10, description="More than 10 concurrent operations"),
                ],
                action=HookAction.ABORT,
                category="performance",
            ),
        ]

        workflow_rules = [
            HookRule(
                name="validate_plan_before_execution",
                description="Ensure execution plan has all required steps and dependencies",
                phase=HookPhase.PRE_PLAN,
                severity=HookSeverity.HIGH,
                conditions=[],
                action=HookAction.CONTINUE,
                category="workflow",
            ),
            HookRule(
                name="check_step_dependencies",
                description="Verify all step dependencies are completed before execution",
                phase=HookPhase.PRE_STEP,
                severity=HookSeverity.HIGH,
                conditions=[
                    HookCondition(field="dependencies_met", operator="eq", value=False, description="Dependencies not met"),
                ],
                action=HookAction.ABORT,
                category="workflow",
            ),
            HookRule(
                name="pass_context_on_delegation",
                description="Ensure relevant context is passed when delegating tasks",
                phase=HookPhase.PRE_DELEGATE,
                severity=HookSeverity.MEDIUM,
                conditions=[
                    HookCondition(field="context_passed", operator="eq", value=False, description="No context passed with delegation"),
                ],
                action=HookAction.MODIFY_PARAMS,
                category="workflow",
            ),
        ]

        for rule in safety_rules + quality_rules + performance_rules + workflow_rules:
            self._rules[rule.id] = rule

    def register_rule(self, rule: HookRule) -> str:
        self._rules[rule.id] = rule
        return rule.id

    def register_handler(self, rule_id: str, handler: Callable):
        self._custom_handlers[rule_id] = handler

    def get_rule(self, rule_id: str) -> Optional[HookRule]:
        return self._rules.get(rule_id)

    def list_rules(self, category: Optional[str] = None, phase: Optional[HookPhase] = None, enabled_only: bool = False) -> List[Dict[str, Any]]:
        results = []
        for rule in self._rules.values():
            if category and rule.category != category:
                continue
            if phase and rule.phase != phase:
                continue
            if enabled_only and not rule.enabled:
                continue
            results.append({
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "phase": rule.phase.value,
                "severity": rule.severity.value,
                "action": rule.action.value,
                "conditions": len(rule.conditions),
                "max_retries": rule.max_retries,
                "timeout_ms": rule.timeout_ms,
                "enabled": rule.enabled,
                "category": rule.category,
                "path_scope": rule.path_scope,
                "agent_scope": rule.agent_scope,
            })
        return results

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = enabled
            return True
        return False

    def _evaluate_condition(self, condition: HookCondition, context: Dict[str, Any]) -> bool:
        field_value = context
        for key in condition.field.split("."):
            if isinstance(field_value, dict):
                field_value = field_value.get(key)
            else:
                return False

        if field_value is None:
            return False

        op = condition.operator
        target = condition.value

        if op == "eq":
            return field_value == target
        elif op == "neq":
            return field_value != target
        elif op == "gt":
            return isinstance(field_value, (int, float)) and field_value > target
        elif op == "gte":
            return isinstance(field_value, (int, float)) and field_value >= target
        elif op == "lt":
            return isinstance(field_value, (int, float)) and field_value < target
        elif op == "lte":
            return isinstance(field_value, (int, float)) and field_value <= target
        elif op == "in":
            return isinstance(target, list) and field_value in target
        elif op == "contains":
            return isinstance(field_value, (str, list)) and target in field_value
        elif op == "matches":
            import re
            return isinstance(field_value, str) and bool(re.search(target, field_value))
        return False

    def evaluate(self, phase: HookPhase, context: Dict[str, Any]) -> List[HookResult]:
        results = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.phase != phase:
                continue
            if rule.path_scope and context.get("path", "").startswith(rule.path_scope):
                pass
            elif rule.path_scope:
                continue
            if rule.agent_scope and context.get("agent_id") != rule.agent_scope:
                continue

            start = time.time()

            if rule.conditions:
                all_met = all(self._evaluate_condition(c, context) for c in rule.conditions)
            else:
                all_met = True

            custom_handler = self._custom_handlers.get(rule.id)
            if custom_handler:
                try:
                    handler_result = custom_handler(context)
                    if isinstance(handler_result, dict):
                        all_met = handler_result.get("passed", all_met)
                        message = handler_result.get("message", "")
                        modified_params = handler_result.get("modified_params")
                    else:
                        all_met = bool(handler_result)
                        message = ""
                        modified_params = None
                except Exception as e:
                    all_met = False
                    message = f"Handler error: {e}"
                    modified_params = None
            else:
                message = f"All conditions {'met' if all_met else 'not met'}"
                modified_params = None

            action = rule.action
            if all_met:
                if action == HookAction.REQUIRE_APPROVAL:
                    approval_id = str(uuid.uuid4())[:8]
                    self._pending_approvals[approval_id] = {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "context": context,
                        "phase": phase.value,
                        "created_at": time.time(),
                    }
                    message = f"Approval required (id: {approval_id})"
            else:
                action = HookAction.CONTINUE
                message = f"Conditions not triggered: {message}"

            result = HookResult(
                rule_id=rule.id,
                rule_name=rule.name,
                action=action,
                passed=action in (HookAction.CONTINUE, HookAction.MODIFY_PARAMS),
                message=message,
                modified_params=modified_params if action == HookAction.MODIFY_PARAMS else None,
                severity=rule.severity,
                duration_ms=(time.time() - start) * 1000,
            )
            results.append(result)

            execution = HookExecution(
                phase=phase,
                rule_id=rule.id,
                result=result,
            )
            self._executions.append(execution)

        if len(self._executions) > self._max_executions:
            self._executions = self._executions[-self._max_executions:]

        return results

    def approve(self, approval_id: str, approved: bool) -> bool:
        approval = self._pending_approvals.get(approval_id)
        if approval:
            approval["approved"] = approved
            approval["resolved_at"] = time.time()
            if not approved:
                approval["action"] = HookAction.ABORT.value
            del self._pending_approvals[approval_id]
            return True
        return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": aid,
                "rule_id": data.get("rule_id"),
                "rule_name": data.get("rule_name"),
                "phase": data.get("phase"),
                "created_at": data.get("created_at"),
            }
            for aid, data in self._pending_approvals.items()
        ]

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [
            {
                "id": ex.id,
                "phase": ex.phase.value,
                "rule_id": ex.rule_id,
                "rule_name": ex.result.rule_name if ex.result else None,
                "action": ex.result.action.value if ex.result else None,
                "passed": ex.result.passed if ex.result else None,
                "message": ex.result.message if ex.result else None,
                "severity": ex.result.severity.value if ex.result else None,
                "timestamp": ex.timestamp,
            }
            for ex in self._executions[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._executions)
        passed = sum(1 for ex in self._executions if ex.result and ex.result.passed)
        by_category = {}
        for rule in self._rules.values():
            by_category[rule.category] = by_category.get(rule.category, 0) + 1
        by_severity = {}
        for ex in self._executions:
            if ex.result:
                sev = ex.result.severity.value
                by_severity[sev] = by_severity.get(sev, 0) + 1
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "total_evaluations": total,
            "passed_evaluations": passed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "pending_approvals": len(self._pending_approvals),
            "rules_by_category": by_category,
            "evaluations_by_severity": by_severity,
        }
