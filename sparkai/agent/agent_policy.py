"""
SparkAI Agent - Policy Engine

Declarative rule-based automation engine that evaluates conditions
against the current system context and triggers automated actions.
Rules are sorted by priority and matched against lane context to
determine what should happen next without human intervention.

Architecture:
  PolicyEngine
    |-- PolicyRule (condition -> action mapping)
    |-- PolicyCondition (AND/OR/NOT composable predicates)
    |-- PolicyAction (automated response types)
    |-- PolicyContext (current system state snapshot)

Supported Actions:
  - Route task to specific agent role
  - Escalate to human with reason
  - Merge/forward work between agents
  - Block operation with reason
  - Recover from failure automatically
  - Notify via channel
  - Chain multiple actions sequentially

Condition Types:
  - Complexity threshold
  - Confidence level
  - Agent workload
  - Failure count
  - Time elapsed
  - Custom predicate evaluation
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class ConditionType(Enum):
    AND = "and"
    OR = "or"
    NOT = "not"
    COMPLEXITY_ABOVE = "complexity_above"
    COMPLEXITY_BELOW = "complexity_below"
    CONFIDENCE_BELOW = "confidence_below"
    CONFIDENCE_ABOVE = "confidence_above"
    WORKLOAD_ABOVE = "workload_above"
    FAILURE_COUNT_ABOVE = "failure_count_above"
    TIME_ELAPSED_ABOVE = "time_elapsed_above"
    AGENT_ROLE_IS = "agent_role_is"
    TASK_TYPE_IS = "task_type_is"
    CUSTOM_PREDICATE = "custom_predicate"


class ActionType(Enum):
    ROUTE_TO_ROLE = "route_to_role"
    ESCALATE = "escalate"
    MERGE_FORWARD = "merge_forward"
    BLOCK = "block"
    RECOVER = "recover"
    NOTIFY = "notify"
    CHAIN = "chain"
    REQUIRE_VERIFICATION = "require_verification"
    SWITCH_STRATEGY = "switch_strategy"
    ADJUST_PRIORITY = "adjust_priority"


@dataclass
class PolicyCondition:
    type: ConditionType = ConditionType.AND
    children: List['PolicyCondition'] = field(default_factory=list)
    threshold: float = 0.0
    value: str = ""
    predicate_name: str = ""

    def evaluate(self, context: 'PolicyContext') -> bool:
        if self.type == ConditionType.AND:
            return all(c.evaluate(context) for c in self.children)
        elif self.type == ConditionType.OR:
            return any(c.evaluate(context) for c in self.children)
        elif self.type == ConditionType.NOT:
            if self.children:
                return not self.children[0].evaluate(context)
            return True
        elif self.type == ConditionType.COMPLEXITY_ABOVE:
            return context.complexity_score > self.threshold
        elif self.type == ConditionType.COMPLEXITY_BELOW:
            return context.complexity_score < self.threshold
        elif self.type == ConditionType.CONFIDENCE_BELOW:
            return context.confidence < self.threshold
        elif self.type == ConditionType.CONFIDENCE_ABOVE:
            return context.confidence > self.threshold
        elif self.type == ConditionType.WORKLOAD_ABOVE:
            return context.agent_workload > self.threshold
        elif self.type == ConditionType.FAILURE_COUNT_ABOVE:
            return context.failure_count > self.threshold
        elif self.type == ConditionType.TIME_ELAPSED_ABOVE:
            return context.time_elapsed > self.threshold
        elif self.type == ConditionType.AGENT_ROLE_IS:
            return context.agent_role == self.value
        elif self.type == ConditionType.TASK_TYPE_IS:
            return context.task_type == self.value
        elif self.type == ConditionType.CUSTOM_PREDICATE:
            return context.evaluate_predicate(self.predicate_name)
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "threshold": self.threshold,
            "value": self.value,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class PolicyAction:
    type: ActionType = ActionType.ESCALATE
    reason: str = ""
    target_role: str = ""
    channel: str = ""
    strategy: str = ""
    priority: int = 0
    chained_actions: List['PolicyAction'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "reason": self.reason,
            "target_role": self.target_role,
            "channel": self.channel,
            "strategy": self.strategy,
            "priority": self.priority,
            "chained_actions": [a.to_dict() for a in self.chained_actions],
        }


@dataclass
class PolicyRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    condition: PolicyCondition = field(default_factory=PolicyCondition)
    actions: List[PolicyAction] = field(default_factory=list)
    priority: int = 50
    enabled: bool = True
    trigger_count: int = 0
    last_triggered: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition.to_dict(),
            "actions": [a.to_dict() for a in self.actions],
            "priority": self.priority,
            "enabled": self.enabled,
            "trigger_count": self.trigger_count,
            "last_triggered": self.last_triggered,
        }


@dataclass
class PolicyContext:
    agent_id: str = ""
    agent_role: str = ""
    task_type: str = ""
    task_id: str = ""
    complexity_score: float = 0.0
    confidence: float = 1.0
    agent_workload: float = 0.0
    failure_count: int = 0
    time_elapsed: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    _predicates: Dict[str, Callable[['PolicyContext'], bool]] = field(default_factory=dict, repr=False)

    def evaluate_predicate(self, name: str) -> bool:
        predicate = self._predicates.get(name)
        if predicate:
            try:
                return predicate(self)
            except Exception:
                return False
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "task_type": self.task_type,
            "complexity_score": self.complexity_score,
            "confidence": self.confidence,
            "agent_workload": self.agent_workload,
            "failure_count": self.failure_count,
            "time_elapsed": self.time_elapsed,
        }


@dataclass
class PolicyEvaluationResult:
    rule_id: str = ""
    rule_name: str = ""
    matched: bool = False
    actions: List[Dict[str, Any]] = field(default_factory=list)
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "matched": self.matched,
            "actions": self.actions,
            "evaluated_at": self.evaluated_at,
        }


class PolicyEngine:
    """
    Declarative policy engine that evaluates rule conditions against
    the current system context and triggers automated actions.

    Rules are sorted by priority (highest first) and the first
    matching rule's actions are executed. This provides a clean
    separation between policy definition and execution logic.

    Usage:
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            name="High Complexity Escalation",
            condition=PolicyCondition(type=ConditionType.COMPLEXITY_ABOVE, threshold=7.0),
            actions=[PolicyAction(type=ActionType.ROUTE_TO_ROLE, target_role="director")],
            priority=80,
        ))
        results = engine.evaluate(context)
    """

    def __init__(self):
        self._rules: Dict[str, PolicyRule] = {}
        self._evaluation_history: List[PolicyEvaluationResult] = []
        self._custom_predicates: Dict[str, Callable[[PolicyContext], bool]] = {}
        self._action_handlers: Dict[ActionType, Callable] = {}
        self._seed_rules()

    def _seed_rules(self) -> None:
        seeds = [
            PolicyRule(
                name="Critical Failure Escalation",
                description="Escalate to human when failure count exceeds threshold",
                condition=PolicyCondition(type=ConditionType.FAILURE_COUNT_ABOVE, threshold=3.0),
                actions=[PolicyAction(type=ActionType.ESCALATE, reason="Failure count exceeded threshold")],
                priority=90,
            ),
            PolicyRule(
                name="High Complexity Director Routing",
                description="Route high-complexity tasks to director role",
                condition=PolicyCondition(type=ConditionType.COMPLEXITY_ABOVE, threshold=7.0),
                actions=[PolicyAction(type=ActionType.ROUTE_TO_ROLE, target_role="director", reason="Task complexity requires director oversight")],
                priority=80,
            ),
            PolicyRule(
                name="Low Confidence Verification",
                description="Require verification when confidence is low",
                condition=PolicyCondition(type=ConditionType.CONFIDENCE_BELOW, threshold=0.5),
                actions=[PolicyAction(type=ActionType.REQUIRE_VERIFICATION, reason="Low confidence result needs verification")],
                priority=75,
            ),
            PolicyRule(
                name="Overloaded Agent Rebalancing",
                description="Switch strategy when agent workload is too high",
                condition=PolicyCondition(type=ConditionType.WORKLOAD_ABOVE, threshold=0.9),
                actions=[PolicyAction(type=ActionType.SWITCH_STRATEGY, strategy="parallel", reason="Agent overloaded, switching to parallel execution")],
                priority=70,
            ),
            PolicyRule(
                name="Worker Task Blocking",
                description="Block workers from performing director-level tasks",
                condition=PolicyCondition(
                    type=ConditionType.AND,
                    children=[
                        PolicyCondition(type=ConditionType.AGENT_ROLE_IS, value="worker"),
                        PolicyCondition(type=ConditionType.COMPLEXITY_ABOVE, threshold=5.0),
                    ],
                ),
                actions=[PolicyAction(type=ActionType.BLOCK, reason="Worker cannot handle high-complexity task")],
                priority=85,
            ),
            PolicyRule(
                name="Timeout Recovery",
                description="Auto-recover when task has been running too long",
                condition=PolicyCondition(type=ConditionType.TIME_ELAPSED_ABOVE, threshold=300.0),
                actions=[PolicyAction(type=ActionType.RECOVER, reason="Task exceeded time limit, initiating recovery")],
                priority=60,
            ),
        ]
        for rule in seeds:
            self._rules[rule.id] = rule

    def add_rule(self, rule: PolicyRule) -> str:
        self._rules[rule.id] = rule
        return rule.id

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def register_predicate(self, name: str, predicate: Callable[[PolicyContext], bool]) -> None:
        self._custom_predicates[name] = predicate

    def register_action_handler(self, action_type: ActionType, handler: Callable) -> None:
        self._action_handlers[action_type] = handler

    def evaluate(self, context: PolicyContext) -> List[PolicyEvaluationResult]:
        context._predicates = self._custom_predicates

        sorted_rules = sorted(
            [r for r in self._rules.values() if r.enabled],
            key=lambda r: r.priority,
            reverse=True,
        )

        results = []
        for rule in sorted_rules:
            matched = rule.condition.evaluate(context)
            result = PolicyEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                matched=matched,
                actions=[a.to_dict() for a in rule.actions] if matched else [],
            )

            if matched:
                rule.trigger_count += 1
                rule.last_triggered = time.time()
                self._execute_actions(rule.actions, context)

            results.append(result)
            self._evaluation_history.append(result)

        return [r for r in results if r.matched]

    def _execute_actions(self, actions: List[PolicyAction], context: PolicyContext) -> None:
        for action in actions:
            if action.type == ActionType.CHAIN:
                self._execute_actions(action.chained_actions, context)
            else:
                handler = self._action_handlers.get(action.type)
                if handler:
                    try:
                        handler(action, context)
                    except Exception:
                        pass

    def list_rules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return sorted([r.to_dict() for r in rules], key=lambda r: r["priority"], reverse=True)

    def get_evaluation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._evaluation_history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total_rules = len(self._rules)
        enabled_rules = sum(1 for r in self._rules.values() if r.enabled)
        total_evaluations = len(self._evaluation_history)
        matched_evaluations = sum(1 for r in self._evaluation_history if r.matched)

        by_action: Dict[str, int] = {}
        for rule in self._rules.values():
            for action in rule.actions:
                by_action[action.type.value] = by_action.get(action.type.value, 0) + 1

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "total_evaluations": total_evaluations,
            "matched_evaluations": matched_evaluations,
            "match_rate": matched_evaluations / max(total_evaluations, 1),
            "by_action_type": by_action,
        }


_global_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    global _global_policy_engine
    if _global_policy_engine is None:
        _global_policy_engine = PolicyEngine()
    return _global_policy_engine
