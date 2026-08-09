"""
SparkLabs Engine - AI Workflow"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ConditionOperator(Enum):
    """Comparison operators for trigger conditions."""
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    CONTAINS = "contains"


class ActionType(Enum):
    """Types of actions a rule can dispatch."""
    DEPLOY_PLOT = "deploy_plot"
    TUNE_PARAMETER = "tune_parameter"
    DEPLOY_DIRECTIVE = "deploy_directive"
    UPDATE_CONTEXT = "update_context"
    RUN_CYCLE = "run_cycle"
    SET_FLAG = "set_flag"
    SEND_ALERT = "send_alert"
    CUSTOM = "custom"


class RuleStatus(Enum):
    """Status of a workflow rule."""
    ACTIVE = "active"
    PAUSED = "paused"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


class WorkflowPhase(Enum):
    """Phases of the workflow evaluation cycle."""
    EVALUATE = "evaluate"
    MATCH = "match"
    DISPATCH = "dispatch"
    EXECUTE = "execute"
    FEEDBACK = "feedback"


class ExecutionResult(Enum):
    """Result of an action execution."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEFERRED = "deferred"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Condition:
    """A single trigger condition."""
    metric: str  # e.g., "player_frustration", "fps", "narrative_tension"
    operator: ConditionOperator
    threshold: float
    label: str = ""


@dataclass
class Action:
    """A single action to execute when a rule triggers."""
    action_type: ActionType
    target_module: str  # e.g., "story_director", "live_tuner", "frame_architect"
    method: str  # method name to call
    params: Dict[str, Any] = field(default_factory=dict)
    label: str = ""


@dataclass
class WorkflowRule:
    """A complete workflow rule: condition(s) -> action(s)."""
    rule_id: str
    name: str
    description: str
    conditions: List[Condition]  # ALL must match (AND logic)
    actions: List[Action]
    priority: int = 0  # higher = more important
    cooldown_s: float = 5.0  # minimum seconds between triggers
    status: RuleStatus = RuleStatus.ACTIVE
    last_triggered: float = 0.0
    trigger_count: int = 0
    last_result: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class ExecutionLog:
    """Log entry for a rule execution."""
    log_id: str
    rule_id: str
    rule_name: str
    triggered_at: float
    actions_executed: int
    results: List[Dict[str, Any]]
    success: bool


@dataclass
class WorkflowStats:
    """Statistics for the workflow engine."""
    total_evaluations: int = 0
    total_triggers: int = 0
    total_actions_executed: int = 0
    total_successes: int = 0
    total_failures: int = 0
    active_rules: int = 0
    last_evaluation_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine AI Workflow
# =============================================================================

class EngineAIWorkflow:
    """
    Singleton declarative workflow engine that chains AI agent actions.

    The engine runs a 5-phase cycle:
      1. EVALUATE  - Read current metric values
      2. MATCH     - Find rules whose conditions are met
      3. DISPATCH  - Sort matched rules by priority
      4. EXECUTE   - Call the target agent methods
      5. FEEDBACK  - Log results and update cooldowns

    Rules connect AI modules: when one module detects a condition, it can
    automatically trigger actions in other modules.
    """

    _instance: Optional["EngineAIWorkflow"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rules: Dict[str, WorkflowRule] = {}
        self._metrics: Dict[str, float] = {}
        self._flags: Dict[str, Any] = {}
        self._execution_log: Deque[ExecutionLog] = deque(maxlen=200)
        self._stats = WorkflowStats()
        self._cycle_count: int = 0
        self._last_cycle_at: float = 0.0
        self._cycle_interval_s: float = 2.0
        self._active: bool = False
        self._action_handlers: Dict[str, Callable[..., Dict[str, Any]]] = {}
        self._register_default_rules()
        self._register_default_handlers()

    @classmethod
    def get_instance(cls) -> "EngineAIWorkflow":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Default Rules
    # -------------------------------------------------------------------------

    def _register_default_rules(self) -> None:
        """Register a set of default workflow rules."""
        defaults = [
            WorkflowRule(
                rule_id="rule_frustration_rescue",
                name="Frustration Rescue",
                description="When player frustration is high, deploy a calming plot and reduce difficulty",
                conditions=[
                    Condition("player_frustration", ConditionOperator.GREATER_THAN, 0.7, "high frustration"),
                ],
                actions=[
                    Action(ActionType.DEPLOY_PLOT, "story_director", "deploy_plot_point",
                           {"plot_type": "REUNION", "characters": ["protagonist"]}, "calming plot"),
                    Action(ActionType.TUNE_PARAMETER, "live_tuner", "set_parameter_by_name",
                           {"param_name": "difficulty", "value": 0.3}, "reduce difficulty"),
                ],
                priority=8,
                cooldown_s=30.0,
            ),
            WorkflowRule(
                rule_id="rule_low_fps_optimize",
                name="Low FPS Optimizer",
                description="When FPS drops below 30, trigger live tuner optimization cycle",
                conditions=[
                    Condition("fps", ConditionOperator.LESS_THAN, 30.0, "low fps"),
                ],
                actions=[
                    Action(ActionType.RUN_CYCLE, "live_tuner", "run_cycle", {}, "tuner cycle"),
                    Action(ActionType.SET_FLAG, "_internal", "set_flag",
                           {"key": "performance_mode", "value": True}, "enable perf mode"),
                ],
                priority=9,
                cooldown_s=10.0,
            ),
            WorkflowRule(
                rule_id="rule_high_tension_cinematic",
                name="High Tension Cinematic",
                description="When narrative tension peaks, switch frame architect to intense mode",
                conditions=[
                    Condition("narrative_tension", ConditionOperator.GREATER_EQUAL, 0.7, "peak tension"),
                ],
                actions=[
                    Action(ActionType.UPDATE_CONTEXT, "frame_architect", "update_context",
                           {"action_intensity": 0.9, "emotional_context": "tense"}, "intense framing"),
                ],
                priority=7,
                cooldown_s=15.0,
            ),
            WorkflowRule(
                rule_id="rule_boss_fight_camera",
                name="Boss Fight Camera",
                description="When boss fight flag is set, configure cinematic camera",
                conditions=[
                    Condition("is_boss_fight", ConditionOperator.EQUAL, 1.0, "boss active"),
                ],
                actions=[
                    Action(ActionType.UPDATE_CONTEXT, "frame_architect", "update_context",
                           {"is_boss_fight": True, "action_intensity": 0.8}, "boss camera"),
                    Action(ActionType.DEPLOY_PLOT, "story_director", "deploy_plot_point",
                           {"plot_type": "CLIMAX", "characters": ["protagonist", "antagonist"]}, "climax plot"),
                ],
                priority=9,
                cooldown_s=60.0,
            ),
            WorkflowRule(
                rule_id="rule_player_idle_engage",
                name="Player Idle Engagement",
                description="When player is idle for too long, introduce a discovery event",
                conditions=[
                    Condition("player_idle_time", ConditionOperator.GREATER_THAN, 30.0, "idle too long"),
                ],
                actions=[
                    Action(ActionType.DEPLOY_PLOT, "story_director", "deploy_plot_point",
                           {"plot_type": "DISCOVERY", "characters": ["protagonist"]}, "discovery event"),
                ],
                priority=5,
                cooldown_s=60.0,
            ),
        ]
        for rule in defaults:
            self._rules[rule.rule_id] = rule

    # -------------------------------------------------------------------------
    # Action Handlers
    # -------------------------------------------------------------------------

    def _register_default_handlers(self) -> None:
        """Register handlers for each action type."""
        self._action_handlers = {
            ActionType.DEPLOY_PLOT.value: self._handle_deploy_plot,
            ActionType.TUNE_PARAMETER.value: self._handle_tune_parameter,
            ActionType.DEPLOY_DIRECTIVE.value: self._handle_deploy_directive,
            ActionType.UPDATE_CONTEXT.value: self._handle_update_context,
            ActionType.RUN_CYCLE.value: self._handle_run_cycle,
            ActionType.SET_FLAG.value: self._handle_set_flag,
            ActionType.SEND_ALERT.value: self._handle_send_alert,
            ActionType.CUSTOM.value: self._handle_custom,
        }

    def _handle_deploy_plot(self, action: Action) -> Dict[str, Any]:
        """Deploy a plot point via the story director."""
        try:
            from sparkai.agent.agent_story_director import AgentStoryDirector
            director = AgentStoryDirector.get_instance()
            plot_type = action.params.get("plot_type", "DISCOVERY")
            characters = action.params.get("characters", [])
            result = director.deploy_plot_point(plot_type, characters=characters)
            return {"success": "error" not in result, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_tune_parameter(self, action: Action) -> Dict[str, Any]:
        """Tune a live tuner parameter."""
        try:
            from sparkai.engine.engine_live_tuner import EngineLiveTuner
            tuner = EngineLiveTuner.get_instance()
            param_name = action.params.get("param_name", "")
            value = action.params.get("value", 0.0)
            # Find parameter by name and set it
            params = tuner.get_parameters()
            target = None
            for p in params:
                if param_name.lower() in p.get("name", "").lower() or param_name.lower() in p.get("param_id", "").lower():
                    target = p
                    break
            if target:
                tuner.set_parameter_value(target["param_id"], float(value))
                return {"success": True, "param_id": target["param_id"], "new_value": value}
            return {"success": False, "error": f"Parameter '{param_name}' not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_deploy_directive(self, action: Action) -> Dict[str, Any]:
        """Deploy a frame directive via the frame architect."""
        try:
            from sparkai.agent.agent_frame_architect import AgentFrameArchitect
            architect = AgentFrameArchitect.get_instance()
            result = architect.run_cycle()
            return {"success": result.get("accepted", False), "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_update_context(self, action: Action) -> Dict[str, Any]:
        """Update the frame architect's scene context."""
        try:
            from sparkai.agent.agent_frame_architect import AgentFrameArchitect
            architect = AgentFrameArchitect.get_instance()
            result = architect.update_context(**action.params)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_run_cycle(self, action: Action) -> Dict[str, Any]:
        """Run a cycle on the target module."""
        try:
            module_name = action.target_module
            if module_name == "live_tuner":
                from sparkai.engine.engine_live_tuner import EngineLiveTuner
                result = EngineLiveTuner.get_instance().run_cycle()
            elif module_name == "story_director":
                from sparkai.agent.agent_story_director import AgentStoryDirector
                result = AgentStoryDirector.get_instance().run_cycle()
            elif module_name == "frame_architect":
                from sparkai.agent.agent_frame_architect import AgentFrameArchitect
                result = AgentFrameArchitect.get_instance().run_cycle()
            else:
                return {"success": False, "error": f"Unknown module: {module_name}"}
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_set_flag(self, action: Action) -> Dict[str, Any]:
        """Set an internal flag."""
        with self._lock:
            key = action.params.get("key", "")
            value = action.params.get("value", True)
            self._flags[key] = value
            return {"success": True, "flag": key, "value": value}

    def _handle_send_alert(self, action: Action) -> Dict[str, Any]:
        """Send an alert (logged)."""
        msg = action.params.get("message", "Alert triggered")
        logger.warning("Workflow alert: %s", msg)
        return {"success": True, "alert": msg}

    def _handle_custom(self, action: Action) -> Dict[str, Any]:
        """Handle a custom action (no-op by default)."""
        return {"success": True, "custom": True, "params": action.params}

    # -------------------------------------------------------------------------
    # Metric Management
    # -------------------------------------------------------------------------

    def report_metric(self, metric_name: str, value: float) -> Dict[str, Any]:
        """Report a metric value for condition evaluation."""
        with self._lock:
            self._metrics[metric_name] = float(value)
            return {"metric": metric_name, "value": value}

    def report_metrics_batch(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Report multiple metrics at once."""
        with self._lock:
            for k, v in metrics.items():
                self._metrics[k] = float(v)
            return {"reported": len(metrics), "total_metrics": len(self._metrics)}

    def get_metrics(self) -> Dict[str, float]:
        """Get all current metric values."""
        with self._lock:
            return dict(self._metrics)

    def get_flags(self) -> Dict[str, Any]:
        """Get all internal flags."""
        with self._lock:
            return dict(self._flags)

    # -------------------------------------------------------------------------
    # Rule Management
    # -------------------------------------------------------------------------

    def add_rule(self, name: str, description: str,
                 conditions: List[Dict[str, Any]],
                 actions: List[Dict[str, Any]],
                 priority: int = 0, cooldown_s: float = 5.0) -> Dict[str, Any]:
        """Add a new workflow rule."""
        with self._lock:
            rule_id = f"rule_{int(time.time() * 1000)}"

            parsed_conditions = []
            for c in conditions:
                op = self._resolve_operator(c.get("operator", "gt"))
                parsed_conditions.append(Condition(
                    metric=c.get("metric", ""),
                    operator=op,
                    threshold=float(c.get("threshold", 0)),
                    label=c.get("label", ""),
                ))

            parsed_actions = []
            for a in actions:
                at = self._resolve_action_type(a.get("action_type", "custom"))
                parsed_actions.append(Action(
                    action_type=at,
                    target_module=a.get("target_module", ""),
                    method=a.get("method", ""),
                    params=a.get("params", {}),
                    label=a.get("label", ""),
                ))

            rule = WorkflowRule(
                rule_id=rule_id,
                name=name,
                description=description,
                conditions=parsed_conditions,
                actions=parsed_actions,
                priority=priority,
                cooldown_s=cooldown_s,
            )
            self._rules[rule_id] = rule
            return self._rule_to_dict(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a workflow rule."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                return True
            return False

    def set_rule_status(self, rule_id: str, status: str) -> Dict[str, Any]:
        """Enable, pause, or disable a rule."""
        with self._lock:
            if rule_id not in self._rules:
                return {"error": f"Rule '{rule_id}' not found"}
            rs = self._resolve_rule_status(status)
            self._rules[rule_id].status = rs
            return {"rule_id": rule_id, "status": rs.value}

    def get_rules(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all rules, optionally filtered by status."""
        with self._lock:
            rules = list(self._rules.values())
            if status_filter:
                rules = [r for r in rules if r.status.value == status_filter]
            return [self._rule_to_dict(r) for r in rules]

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a single rule by ID."""
        with self._lock:
            rule = self._rules.get(rule_id)
            return self._rule_to_dict(rule) if rule else None

    # -------------------------------------------------------------------------
    # Condition Evaluation
    # -------------------------------------------------------------------------

    def _evaluate_condition(self, cond: Condition) -> bool:
        """Evaluate a single condition against current metrics."""
        value = self._metrics.get(cond.metric)
        if value is None:
            # Check flags for boolean metrics
            flag_val = self._flags.get(cond.metric)
            if flag_val is not None:
                value = 1.0 if flag_val else 0.0
            else:
                return False

        if cond.operator == ConditionOperator.GREATER_THAN:
            return value > cond.threshold
        elif cond.operator == ConditionOperator.LESS_THAN:
            return value < cond.threshold
        elif cond.operator == ConditionOperator.GREATER_EQUAL:
            return value >= cond.threshold
        elif cond.operator == ConditionOperator.LESS_EQUAL:
            return value <= cond.threshold
        elif cond.operator == ConditionOperator.EQUAL:
            return abs(value - cond.threshold) < 0.001
        elif cond.operator == ConditionOperator.NOT_EQUAL:
            return abs(value - cond.threshold) >= 0.001
        elif cond.operator == ConditionOperator.CONTAINS:
            return cond.threshold in str(value)
        return False

    def _evaluate_rule(self, rule: WorkflowRule) -> bool:
        """Evaluate all conditions of a rule (AND logic)."""
        if rule.status in (RuleStatus.DISABLED, RuleStatus.PAUSED):
            return False
        if rule.status == RuleStatus.COOLDOWN:
            if time.time() - rule.last_triggered < rule.cooldown_s:
                return False
            rule.status = RuleStatus.ACTIVE
        return all(self._evaluate_condition(c) for c in rule.conditions)

    # -------------------------------------------------------------------------
    # Workflow Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single workflow evaluation cycle.

        Phases: EVALUATE -> MATCH -> DISPATCH -> EXECUTE -> FEEDBACK
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = WorkflowPhase.EVALUATE

            # Phase 1: EVALUATE - metrics are already up to date
            phase = WorkflowPhase.MATCH

            # Phase 2: MATCH - find rules whose conditions are met
            matched_rules: List[WorkflowRule] = []
            for rule in self._rules.values():
                if self._evaluate_rule(rule):
                    matched_rules.append(rule)

            # Phase 3: DISPATCH - sort by priority (descending)
            phase = WorkflowPhase.DISPATCH
            matched_rules.sort(key=lambda r: r.priority, reverse=True)

            # Phase 4: EXECUTE - run actions
            phase = WorkflowPhase.EXECUTE
            executed_count = 0
            success_count = 0
            cycle_results: List[Dict[str, Any]] = []

            for rule in matched_rules:
                now = time.time()
                rule.last_triggered = now
                rule.trigger_count += 1
                rule.status = RuleStatus.COOLDOWN
                self._stats.total_triggers += 1

                action_results: List[Dict[str, Any]] = []
                rule_success = True

                for action in rule.actions:
                    handler = self._action_handlers.get(action.action_type.value, self._handle_custom)
                    try:
                        result = handler(action)
                        action_results.append({
                            "action_type": action.action_type.value,
                            "target_module": action.target_module,
                            "label": action.label,
                            "result": result,
                        })
                        executed_count += 1
                        self._stats.total_actions_executed += 1
                        if result.get("success"):
                            self._stats.total_successes += 1
                        else:
                            self._stats.total_failures += 1
                            rule_success = False
                    except Exception as e:
                        action_results.append({
                            "action_type": action.action_type.value,
                            "error": str(e),
                        })
                        self._stats.total_failures += 1
                        rule_success = False

                rule.last_result = "success" if rule_success else "failed"

                log_entry = ExecutionLog(
                    log_id=f"log_{int(now * 1000)}_{rule.trigger_count}",
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    triggered_at=now,
                    actions_executed=len(rule.actions),
                    results=action_results,
                    success=rule_success,
                )
                self._execution_log.append(log_entry)
                cycle_results.append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "success": rule_success,
                    "actions": action_results,
                })

                if rule_success:
                    success_count += 1

            # Phase 5: FEEDBACK
            phase = WorkflowPhase.FEEDBACK
            self._cycle_count += 1
            self._stats.total_evaluations += 1
            self._stats.active_rules = sum(1 for r in self._rules.values() if r.status == RuleStatus.ACTIVE)
            self._stats.last_evaluation_time_ms = (time.time() - start_time) * 1000
            self._stats.active = True
            self._last_cycle_at = time.time()

            return {
                "phase": phase.value,
                "rules_evaluated": len(self._rules),
                "rules_matched": len(matched_rules),
                "rules_triggered": len(cycle_results),
                "actions_executed": executed_count,
                "successes": success_count,
                "cycle": self._cycle_count,
                "results": cycle_results,
            }

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the workflow engine."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_rules": len(self._rules),
                "active_rules": sum(1 for r in self._rules.values() if r.status == RuleStatus.ACTIVE),
                "cooldown_rules": sum(1 for r in self._rules.values() if r.status == RuleStatus.COOLDOWN),
                "total_metrics": len(self._metrics),
                "total_flags": len(self._flags),
                "stats": {
                    "total_evaluations": self._stats.total_evaluations,
                    "total_triggers": self._stats.total_triggers,
                    "total_actions_executed": self._stats.total_actions_executed,
                    "total_successes": self._stats.total_successes,
                    "total_failures": self._stats.total_failures,
                    "active_rules": self._stats.active_rules,
                    "last_evaluation_time_ms": round(self._stats.last_evaluation_time_ms, 2),
                    "active": self._stats.active,
                },
            }

    def get_execution_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent execution log entries."""
        with self._lock:
            log = list(self._execution_log)
            if limit > 0:
                log = log[-limit:]
            return [self._log_to_dict(l) for l in reversed(log)]

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles with simulated metric changes."""
        with self._lock:
            import random
            total_triggers = 0
            total_actions = 0

            for i in range(cycles):
                # Simulate varying metrics
                self.report_metrics_batch({
                    "player_frustration": random.uniform(0, 1),
                    "fps": random.uniform(20, 70),
                    "narrative_tension": random.uniform(0, 1),
                    "is_boss_fight": float(random.choice([0, 0, 0, 1])),
                    "player_idle_time": random.uniform(0, 60),
                    "player_health": random.uniform(0.2, 1.0),
                })
                result = self.run_cycle()
                total_triggers += result.get("rules_triggered", 0)
                total_actions += result.get("actions_executed", 0)

            return {
                "cycles_run": cycles,
                "total_triggers": total_triggers,
                "total_actions": total_actions,
                "final_metrics": len(self._metrics),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the workflow engine to initial state."""
        with self._lock:
            self._rules.clear()
            self._metrics.clear()
            self._flags.clear()
            self._execution_log.clear()
            self._stats = WorkflowStats()
            self._cycle_count = 0
            self._last_cycle_at = 0.0
            self._active = False
            self._register_default_rules()
            return {"reset": True, "rules_registered": len(self._rules)}

    # -------------------------------------------------------------------------
    # Enum Resolvers (case-insensitive)
    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_operator(name: str) -> ConditionOperator:
        key = name.strip().lower()
        for op in ConditionOperator:
            if op.value == key or op.name.lower() == key:
                return op
        return ConditionOperator.GREATER_THAN

    @staticmethod
    def _resolve_action_type(name: str) -> ActionType:
        key = name.strip().lower()
        for at in ActionType:
            if at.value == key or at.name.lower() == key:
                return at
        return ActionType.CUSTOM

    @staticmethod
    def _resolve_rule_status(name: str) -> RuleStatus:
        key = name.strip().lower()
        for rs in RuleStatus:
            if rs.value == key or rs.name.lower() == key:
                return rs
        return RuleStatus.ACTIVE

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _rule_to_dict(self, rule: WorkflowRule) -> Dict[str, Any]:
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "conditions": [
                {
                    "metric": c.metric,
                    "operator": c.operator.value,
                    "threshold": c.threshold,
                    "label": c.label,
                }
                for c in rule.conditions
            ],
            "actions": [
                {
                    "action_type": a.action_type.value,
                    "target_module": a.target_module,
                    "method": a.method,
                    "params": a.params,
                    "label": a.label,
                }
                for a in rule.actions
            ],
            "priority": rule.priority,
            "cooldown_s": rule.cooldown_s,
            "status": rule.status.value,
            "last_triggered": rule.last_triggered,
            "trigger_count": rule.trigger_count,
            "last_result": rule.last_result,
            "created_at": rule.created_at,
        }

    def _log_to_dict(self, log: ExecutionLog) -> Dict[str, Any]:
        return {
            "log_id": log.log_id,
            "rule_id": log.rule_id,
            "rule_name": log.rule_name,
            "triggered_at": log.triggered_at,
            "actions_executed": log.actions_executed,
            "results": log.results,
            "success": log.success,
        }
