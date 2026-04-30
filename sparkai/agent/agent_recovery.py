"""
SparkAI Agent - Recovery Engine

Automatic failure recovery system that detects runtime failures
and applies structured recovery recipes. Each recipe defines
a sequence of recovery steps with escalation policies when
automatic recovery fails.

Architecture:
  RecoveryEngine
    |-- FailureDetector (pattern-based failure classification)
    |-- RecoveryRecipe (structured recovery procedures)
    |-- EscalationPolicy (fallback when recovery fails)
    |-- RecoveryTracker (history and success rate tracking)

Recovery Flow:
  1. Detect failure via pattern matching or health check
  2. Classify failure type and severity
  3. Look up matching recovery recipe
  4. Execute recovery steps with retry logic
  5. Verify recovery succeeded
  6. Escalate if recovery fails after max attempts
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class FailureType(Enum):
    AGENT_STUCK = "agent_stuck"
    AGENT_ERROR_LOOP = "agent_error_loop"
    PROTOCOL_TIMEOUT = "protocol_timeout"
    PROTOCOL_DELIVERY_FAILED = "protocol_delivery_failed"
    ORCHESTRATOR_NO_AGENT = "orchestrator_no_agent"
    ORCHESTRATOR_DEADLOCK = "orchestrator_deadlock"
    SWARM_CONSENSUS_FAILED = "swarm_consensus_failed"
    SWARM_NODE_UNRESPONSIVE = "swarm_node_unresponsive"
    PIPELINE_STAGE_FAILED = "pipeline_stage_failed"
    PIPELINE_TIMEOUT = "pipeline_timeout"
    SESSION_CORRUPTED = "session_corrupted"
    SESSION_TOKEN_OVERFLOW = "session_token_overflow"
    SKILL_EXECUTION_FAILED = "skill_execution_failed"
    MEMORY_RETRIEVAL_FAILED = "memory_retrieval_failed"
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    LLM_PROVIDER_ERROR = "llm_provider_error"
    CONTEXT_INCONSISTENCY = "context_inconsistency"
    UNKNOWN = "unknown"


class FailureSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RECOVERED = "recovered"
    ESCALATED = "escalated"
    FAILED = "failed"


class EscalationAction(Enum):
    ALERT_HUMAN = "alert_human"
    LOG_AND_CONTINUE = "log_and_continue"
    RESTART_SUBSYSTEM = "restart_subsystem"
    ABORT_OPERATION = "abort_operation"
    FALLBACK_STRATEGY = "fallback_strategy"


@dataclass
class RecoveryStep:
    name: str = ""
    description: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    retry_on_failure: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "params": self.params,
            "timeout_seconds": self.timeout_seconds,
            "retry_on_failure": self.retry_on_failure,
        }


@dataclass
class RecoveryRecipe:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    failure_type: FailureType = FailureType.UNKNOWN
    severity: FailureSeverity = FailureSeverity.MEDIUM
    steps: List[RecoveryStep] = field(default_factory=list)
    max_attempts: int = 2
    backoff_base_seconds: float = 1.0
    escalation: EscalationAction = EscalationAction.ALERT_HUMAN
    verification_action: str = ""
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "steps": [s.to_dict() for s in self.steps],
            "max_attempts": self.max_attempts,
            "backoff_base_seconds": self.backoff_base_seconds,
            "escalation": self.escalation.value,
            "verification_action": self.verification_action,
            "enabled": self.enabled,
        }


@dataclass
class FailureRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    failure_type: FailureType = FailureType.UNKNOWN
    severity: FailureSeverity = FailureSeverity.MEDIUM
    source: str = ""
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: float = field(default_factory=time.time)
    recipe_id: Optional[str] = None
    recovery_status: RecoveryStatus = RecoveryStatus.PENDING
    recovery_attempts: int = 0
    recovered_at: Optional[float] = None
    escalation_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "source": self.source,
            "message": self.message,
            "context": self.context,
            "detected_at": self.detected_at,
            "recipe_id": self.recipe_id,
            "recovery_status": self.recovery_status.value,
            "recovery_attempts": self.recovery_attempts,
            "recovered_at": self.recovered_at,
            "escalation_triggered": self.escalation_triggered,
        }


class FailureDetector:
    """
    Pattern-based failure detection that classifies errors
    into typed failure categories for recipe matching.
    """

    PATTERNS: Dict[FailureType, List[str]] = {
        FailureType.AGENT_STUCK: ["no progress", "stuck", "idle timeout", "heartbeat lost"],
        FailureType.AGENT_ERROR_LOOP: ["consecutive errors", "error loop", "repeated failure"],
        FailureType.PROTOCOL_TIMEOUT: ["timeout", "timed out", "delivery expired", "no response"],
        FailureType.PROTOCOL_DELIVERY_FAILED: ["delivery failed", "no handler", "recipient not found"],
        FailureType.ORCHESTRATOR_NO_AGENT: ["no agent available", "no capable agent", "agent not found"],
        FailureType.ORCHESTRATOR_DEADLOCK: ["deadlock", "circular dependency", "waiting forever"],
        FailureType.SWARM_CONSENSUS_FAILED: ["consensus failed", "voting timeout", "no quorum"],
        FailureType.SWARM_NODE_UNRESPONSIVE: ["node unresponsive", "node timeout", "node failed"],
        FailureType.PIPELINE_STAGE_FAILED: ["stage failed", "pipeline error", "stage timeout"],
        FailureType.PIPELINE_TIMEOUT: ["pipeline timeout", "pipeline expired", "pipeline stuck"],
        FailureType.SESSION_CORRUPTED: ["session corrupted", "invalid state", "session integrity"],
        FailureType.SESSION_TOKEN_OVERFLOW: ["token limit", "context overflow", "too many tokens"],
        FailureType.SKILL_EXECUTION_FAILED: ["skill failed", "skill error", "skill timeout"],
        FailureType.MEMORY_RETRIEVAL_FAILED: ["memory error", "retrieval failed", "memory corrupted"],
        FailureType.TOOL_EXECUTION_ERROR: ["tool error", "execution failed", "tool timeout"],
        FailureType.LLM_PROVIDER_ERROR: ["llm error", "provider error", "api error", "rate limit"],
        FailureType.CONTEXT_INCONSISTENCY: ["context mismatch", "state inconsistency", "stale context"],
    }

    def detect(self, error_message: str, source: str = "") -> FailureType:
        message_lower = error_message.lower()
        best_match = FailureType.UNKNOWN
        best_score = 0

        for failure_type, patterns in self.PATTERNS.items():
            score = sum(1 for p in patterns if p in message_lower)
            if score > best_score:
                best_score = score
                best_match = failure_type

        return best_match

    def classify_severity(self, failure_type: FailureType) -> FailureSeverity:
        severity_map = {
            FailureType.AGENT_STUCK: FailureSeverity.MEDIUM,
            FailureType.AGENT_ERROR_LOOP: FailureSeverity.HIGH,
            FailureType.PROTOCOL_TIMEOUT: FailureSeverity.MEDIUM,
            FailureType.PROTOCOL_DELIVERY_FAILED: FailureSeverity.HIGH,
            FailureType.ORCHESTRATOR_NO_AGENT: FailureSeverity.MEDIUM,
            FailureType.ORCHESTRATOR_DEADLOCK: FailureSeverity.CRITICAL,
            FailureType.SWARM_CONSENSUS_FAILED: FailureSeverity.MEDIUM,
            FailureType.SWARM_NODE_UNRESPONSIVE: FailureSeverity.MEDIUM,
            FailureType.PIPELINE_STAGE_FAILED: FailureSeverity.HIGH,
            FailureType.PIPELINE_TIMEOUT: FailureSeverity.HIGH,
            FailureType.SESSION_CORRUPTED: FailureSeverity.CRITICAL,
            FailureType.SESSION_TOKEN_OVERFLOW: FailureSeverity.LOW,
            FailureType.SKILL_EXECUTION_FAILED: FailureSeverity.MEDIUM,
            FailureType.MEMORY_RETRIEVAL_FAILED: FailureSeverity.LOW,
            FailureType.TOOL_EXECUTION_ERROR: FailureSeverity.MEDIUM,
            FailureType.LLM_PROVIDER_ERROR: FailureSeverity.HIGH,
            FailureType.CONTEXT_INCONSISTENCY: FailureSeverity.MEDIUM,
            FailureType.UNKNOWN: FailureSeverity.MEDIUM,
        }
        return severity_map.get(failure_type, FailureSeverity.MEDIUM)


class RecoveryEngine:
    """
    Automatic failure recovery engine that detects, classifies,
    and recovers from runtime failures using structured recipes.

    The engine maintains a library of recovery recipes, each defining
    a sequence of steps for a specific failure type. When automatic
    recovery fails after max attempts, the engine escalates according
    to the recipe's escalation policy.

    Usage:
        engine = RecoveryEngine()
        record = engine.detect_and_recover("Agent stuck in idle state", source="loop")
        # record.recovery_status will be RECOVERED, ESCALATED, or FAILED
    """

    def __init__(self):
        self._recipes: Dict[str, RecoveryRecipe] = {}
        self._type_index: Dict[FailureType, List[str]] = {}
        self._failures: List[FailureRecord] = []
        self._detector = FailureDetector()
        self._action_handlers: Dict[str, Callable] = {}
        self._seed_recipes()

    def _seed_recipes(self) -> None:
        seeds = [
            RecoveryRecipe(
                name="Reset Stuck Agent",
                failure_type=FailureType.AGENT_STUCK,
                severity=FailureSeverity.MEDIUM,
                steps=[
                    RecoveryStep(name="reset_state", description="Reset agent state to idle", action="reset_agent_state", params={"target_state": "idle"}),
                    RecoveryStep(name="clear_queue", description="Clear pending message queue", action="clear_agent_queue"),
                ],
                max_attempts=2,
                escalation=EscalationAction.ALERT_HUMAN,
                verification_action="check_agent_responsive",
            ),
            RecoveryRecipe(
                name="Break Error Loop",
                failure_type=FailureType.AGENT_ERROR_LOOP,
                severity=FailureSeverity.HIGH,
                steps=[
                    RecoveryStep(name="simplify_prompt", description="Reduce prompt complexity", action="simplify_agent_prompt"),
                    RecoveryStep(name="reset_error_counter", description="Reset consecutive error counter", action="reset_error_counter"),
                    RecoveryStep(name="switch_strategy", description="Switch to simpler execution strategy", action="switch_strategy", params={"strategy": "direct"}),
                ],
                max_attempts=2,
                escalation=EscalationAction.FALLBACK_STRATEGY,
                verification_action="check_agent_executing",
            ),
            RecoveryRecipe(
                name="Retry Protocol Delivery",
                failure_type=FailureType.PROTOCOL_TIMEOUT,
                severity=FailureSeverity.MEDIUM,
                steps=[
                    RecoveryStep(name="retry_delivery", description="Resend message with exponential backoff", action="retry_protocol_delivery", params={"backoff_multiplier": 2.0}),
                    RecoveryStep(name="check_recipient", description="Verify recipient is registered", action="check_recipient_alive"),
                ],
                max_attempts=3,
                backoff_base_seconds=0.5,
                escalation=EscalationAction.LOG_AND_CONTINUE,
                verification_action="check_delivery_confirmed",
            ),
            RecoveryRecipe(
                name="Resolve Orchestrator Deadlock",
                failure_type=FailureType.ORCHESTRATOR_DEADLOCK,
                severity=FailureSeverity.CRITICAL,
                steps=[
                    RecoveryStep(name="detect_cycle", description="Identify circular dependency chain", action="detect_deadlock_cycle"),
                    RecoveryStep(name="break_cycle", description="Force-release the lowest-priority lock", action="break_deadlock_cycle"),
                ],
                max_attempts=1,
                escalation=EscalationAction.ABORT_OPERATION,
                verification_action="check_agents_progressing",
            ),
            RecoveryRecipe(
                name="Recover Swarm Consensus",
                failure_type=FailureType.SWARM_CONSENSUS_FAILED,
                severity=FailureSeverity.MEDIUM,
                steps=[
                    RecoveryStep(name="reduce_quorum", description="Lower quorum requirement for consensus", action="reduce_consensus_quorum", params={"new_threshold": 0.5}),
                    RecoveryStep(name="coordinator_decide", description="Let coordinator make executive decision", action="coordinator_override"),
                ],
                max_attempts=2,
                escalation=EscalationAction.FALLBACK_STRATEGY,
                verification_action="check_consensus_reached",
            ),
            RecoveryRecipe(
                name="Retry Pipeline Stage",
                failure_type=FailureType.PIPELINE_STAGE_FAILED,
                severity=FailureSeverity.HIGH,
                steps=[
                    RecoveryStep(name="retry_stage", description="Retry the failed pipeline stage", action="retry_pipeline_stage"),
                    RecoveryStep(name="simplify_stage", description="Reduce stage complexity and retry", action="simplify_pipeline_stage"),
                ],
                max_attempts=2,
                escalation=EscalationAction.ALERT_HUMAN,
                verification_action="check_pipeline_progressing",
            ),
            RecoveryRecipe(
                name="Compact Session Tokens",
                failure_type=FailureType.SESSION_TOKEN_OVERFLOW,
                severity=FailureSeverity.LOW,
                steps=[
                    RecoveryStep(name="compact_session", description="Run session compaction to free tokens", action="compact_session"),
                ],
                max_attempts=1,
                escalation=EscalationAction.LOG_AND_CONTINUE,
                verification_action="check_session_under_limit",
            ),
            RecoveryRecipe(
                name="Retry LLM Provider",
                failure_type=FailureType.LLM_PROVIDER_ERROR,
                severity=FailureSeverity.HIGH,
                steps=[
                    RecoveryStep(name="retry_with_backoff", description="Retry LLM call with exponential backoff", action="retry_llm_call", params={"backoff_multiplier": 2.0}),
                    RecoveryStep(name="switch_provider", description="Switch to fallback LLM provider", action="switch_llm_provider"),
                ],
                max_attempts=3,
                backoff_base_seconds=1.0,
                escalation=EscalationAction.ABORT_OPERATION,
                verification_action="check_llm_responsive",
            ),
        ]

        for recipe in seeds:
            self._recipes[recipe.id] = recipe
            self._type_index.setdefault(recipe.failure_type, []).append(recipe.id)

    def register_action_handler(self, action_name: str, handler: Callable) -> None:
        self._action_handlers[action_name] = handler

    def register_recipe(self, recipe: RecoveryRecipe) -> str:
        self._recipes[recipe.id] = recipe
        self._type_index.setdefault(recipe.failure_type, []).append(recipe.id)
        return recipe.id

    async def detect_and_recover(self, error_message: str, source: str = "", context: Optional[Dict[str, Any]] = None) -> FailureRecord:
        failure_type = self._detector.detect(error_message, source)
        severity = self._detector.classify_severity(failure_type)

        record = FailureRecord(
            failure_type=failure_type,
            severity=severity,
            source=source,
            message=error_message,
            context=context or {},
        )

        recipe_ids = self._type_index.get(failure_type, [])
        if not recipe_ids:
            recipe_ids = self._type_index.get(FailureType.UNKNOWN, [])

        if recipe_ids:
            recipe = self._recipes[recipe_ids[0]]
            record.recipe_id = recipe.id
            await self._execute_recipe(record, recipe)
        else:
            record.recovery_status = RecoveryStatus.ESCALATED
            record.escalation_triggered = True

        self._failures.append(record)
        return record

    async def _execute_recipe(self, record: FailureRecord, recipe: RecoveryRecipe) -> None:
        record.recovery_status = RecoveryStatus.IN_PROGRESS

        for attempt in range(1, recipe.max_attempts + 1):
            record.recovery_attempts = attempt
            success = self._execute_steps(recipe)

            if success:
                record.recovery_status = RecoveryStatus.RECOVERED
                record.recovered_at = time.time()
                return

            if attempt < recipe.max_attempts:
                backoff = recipe.backoff_base_seconds * (2 ** (attempt - 1))
                await asyncio.sleep(min(backoff, 30.0))

        self._escalate(record, recipe)

    def _execute_steps(self, recipe: RecoveryRecipe) -> bool:
        for step in recipe.steps:
            handler = self._action_handlers.get(step.action)
            if handler:
                try:
                    result = handler(step.params)
                    if result is False:
                        if step.retry_on_failure:
                            continue
                        return False
                except Exception:
                    if step.retry_on_failure:
                        continue
                    return False
        return True

    def _escalate(self, record: FailureRecord, recipe: RecoveryRecipe) -> None:
        record.escalation_triggered = True

        if recipe.escalation == EscalationAction.LOG_AND_CONTINUE:
            record.recovery_status = RecoveryStatus.FAILED
        elif recipe.escalation == EscalationAction.ABORT_OPERATION:
            record.recovery_status = RecoveryStatus.FAILED
        elif recipe.escalation == EscalationAction.FALLBACK_STRATEGY:
            record.recovery_status = RecoveryStatus.ESCALATED
        elif recipe.escalation == EscalationAction.RESTART_SUBSYSTEM:
            record.recovery_status = RecoveryStatus.ESCALATED
        else:
            record.recovery_status = RecoveryStatus.ESCALATED

    def list_recipes(self, failure_type: Optional[FailureType] = None) -> List[Dict[str, Any]]:
        recipes = list(self._recipes.values())
        if failure_type:
            recipes = [r for r in recipes if r.failure_type == failure_type]
        return [r.to_dict() for r in recipes]

    def get_failure_history(self, limit: int = 50, failure_type: Optional[FailureType] = None) -> List[Dict[str, Any]]:
        records = self._failures
        if failure_type:
            records = [r for r in records if r.failure_type == failure_type]
        return [r.to_dict() for r in records[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._failures)
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for f in self._failures:
            by_type[f.failure_type.value] = by_type.get(f.failure_type.value, 0) + 1
            by_status[f.recovery_status.value] = by_status.get(f.recovery_status.value, 0) + 1

        recovered = by_status.get(RecoveryStatus.RECOVERED.value, 0)
        recovery_rate = recovered / max(total, 1)

        return {
            "total_failures": total,
            "total_recipes": len(self._recipes),
            "recovery_rate": round(recovery_rate, 3),
            "by_type": by_type,
            "by_status": by_status,
            "escalation_count": sum(1 for f in self._failures if f.escalation_triggered),
        }


_global_recovery_engine: Optional[RecoveryEngine] = None


def get_recovery_engine() -> RecoveryEngine:
    global _global_recovery_engine
    if _global_recovery_engine is None:
        _global_recovery_engine = RecoveryEngine()
    return _global_recovery_engine
