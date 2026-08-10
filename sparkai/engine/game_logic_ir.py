"""
SparkAI Engine - Game Logic IR (Intermediate Representation)"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConditionOperator(Enum):
    """Comparison operators for conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    IS_NULL = "is_null"
    NOT_NULL = "not_null"
    BETWEEN = "between"
    IN_SET = "in_set"


class ActionType(Enum):
    """Types of actions that can be triggered."""
    SPAWN_ENTITY = "spawn_entity"
    DESTROY_ENTITY = "destroy_entity"
    MOVE_ENTITY = "move_entity"
    SET_PROPERTY = "set_property"
    PLAY_ANIMATION = "play_animation"
    PLAY_SOUND = "play_sound"
    EMIT_SIGNAL = "emit_signal"
    CHANGE_SCENE = "change_scene"
    ADD_SCORE = "add_score"
    SET_VARIABLE = "set_variable"
    TOGGLE_PAUSE = "toggle_pause"
    DISPLAY_TEXT = "display_text"
    DAMAGE_ENTITY = "damage_entity"
    HEAL_ENTITY = "heal_entity"
    ADD_COMPONENT = "add_component"
    REMOVE_COMPONENT = "remove_component"
    TRIGGER_EVENT = "trigger_event"
    CUSTOM = "custom"


@dataclass
class Expression:
    """A structured expression in the IR. Can be a literal, variable reference, or computed."""
    type: str = "literal"  # "literal", "variable", "computed"
    value: Any = None
    variable_path: str = ""  # e.g., "player.health" or "game.score"
    operator: str = ""  # For computed expressions
    operands: List["Expression"] = field(default_factory=list)

    def evaluate(self, context: Dict[str, Any]) -> Any:
        if self.type == "literal":
            return self.value
        elif self.type == "variable":
            return self._resolve_variable(context)
        elif self.type == "computed":
            return self._compute(context)
        return None

    def _resolve_variable(self, context: Dict[str, Any]) -> Any:
        parts = self.variable_path.split(".")
        current = context
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _compute(self, context: Dict[str, Any]) -> Any:
        left = self.operands[0].evaluate(context) if self.operands else 0
        right = self.operands[1].evaluate(context) if len(self.operands) > 1 else 0

        ops = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b if b != 0 else 0,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "and": lambda a, b: a and b,
            "or": lambda a, b: a or b,
        }
        func = ops.get(self.operator)
        if func:
            return func(left, right)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "value": self.value,
            "variable_path": self.variable_path,
            "operator": self.operator,
            "operands": [o.to_dict() for o in self.operands],
        }


@dataclass
class Condition:
    """A single condition that must be met for an action to execute."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    left: Expression = field(default_factory=Expression)
    operator: ConditionOperator = ConditionOperator.EQUALS
    right: Expression = field(default_factory=Expression)

    def evaluate(self, context: Dict[str, Any]) -> bool:
        left_val = self.left.evaluate(context)
        right_val = self.right.evaluate(context)

        ops = {
            ConditionOperator.EQUALS: lambda: left_val == right_val,
            ConditionOperator.NOT_EQUALS: lambda: left_val != right_val,
            ConditionOperator.GREATER_THAN: lambda: left_val > right_val,
            ConditionOperator.LESS_THAN: lambda: left_val < right_val,
            ConditionOperator.GREATER_EQUAL: lambda: left_val >= right_val,
            ConditionOperator.LESS_EQUAL: lambda: left_val <= right_val,
            ConditionOperator.CONTAINS: lambda: str(right_val) in str(left_val),
            ConditionOperator.STARTS_WITH: lambda: str(left_val).startswith(str(right_val)),
            ConditionOperator.IS_NULL: lambda: left_val is None,
            ConditionOperator.NOT_NULL: lambda: left_val is not None,
            ConditionOperator.BETWEEN: lambda: self._between_check(left_val, right_val),
            ConditionOperator.IN_SET: lambda: left_val in (right_val if isinstance(right_val, (list, tuple)) else [right_val]),
        }
        func = ops.get(self.operator)
        if func:
            return bool(func())
        return False

    def _between_check(self, value: Any, bounds: Any) -> bool:
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            return bounds[0] <= value <= bounds[1]
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "left": self.left.to_dict(),
            "operator": self.operator.value,
            "right": self.right.to_dict(),
        }


@dataclass
class GameAction:
    """A single action to execute when conditions are met."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    action_type: ActionType = ActionType.SPAWN_ENTITY
    target: str = ""  # Entity ID, scene name, or "self"
    params: Dict[str, Any] = field(default_factory=dict)
    delay_ms: int = 0  # Delay before executing
    repeat_count: int = 1  # How many times to repeat

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "target": self.target,
            "params": self.params,
            "delay_ms": self.delay_ms,
            "repeat_count": self.repeat_count,
        }


@dataclass
class GameEvent:
    """A complete event with typed conditions and actions."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "Untitled Event"
    description: str = ""
    conditions: List[Condition] = field(default_factory=list)
    actions: List[GameAction] = field(default_factory=list)
    enabled: bool = True
    trigger_count: int = 0
    max_triggers: int = -1  # -1 = unlimited
    cooldown_ms: int = 0
    last_triggered: float = 0.0
    priority: int = 0

    def can_trigger(self, context: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        if self.max_triggers > 0 and self.trigger_count >= self.max_triggers:
            return False
        if self.cooldown_ms > 0:
            elapsed = (time.time() - self.last_triggered) * 1000
            if elapsed < self.cooldown_ms:
                return False
        for cond in self.conditions:
            if not cond.evaluate(context):
                return False
        return True

    def mark_triggered(self) -> None:
        self.trigger_count += 1
        self.last_triggered = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "enabled": self.enabled,
            "trigger_count": self.trigger_count,
            "max_triggers": self.max_triggers,
            "cooldown_ms": self.cooldown_ms,
            "priority": self.priority,
        }


class GameLogicCompiler:
    """
    Compiles a GameEvent into executable runtime logic.

    The AI emits structured events (conditions + actions + expressions).
    This compiler validates them, prepares execution, and returns a
    compiled event ready for the engine's game loop.
    """

    def __init__(self):
        self._compiled_cache: Dict[str, CompiledEvent] = {}
        self._handlers: Dict[ActionType, Callable] = {}

    def register_handler(self, action_type: ActionType, handler: Callable) -> None:
        self._handlers[action_type] = handler

    def compile(self, event: GameEvent) -> "CompiledEvent":
        """Compile a GameEvent into an executable form."""
        compiled = CompiledEvent(
            event_id=event.id,
            name=event.name,
            conditions=event.conditions,
            actions=event.actions,
            priority=event.priority,
        )
        self._compiled_cache[event.id] = compiled
        return compiled

    def compile_batch(self, events: List[GameEvent]) -> List["CompiledEvent"]:
        """Compile multiple events at once."""
        return [self.compile(e) for e in events]

    def validate(self, event: GameEvent) -> Dict[str, Any]:
        """Validate an event before compilation. Returns validation results."""
        issues = []
        warnings = []

        if not event.name:
            issues.append("Event must have a name")

        if not event.conditions:
            warnings.append("Event has no conditions - will always trigger")

        if not event.actions:
            issues.append("Event must have at least one action")

        for i, action in enumerate(event.actions):
            if action.action_type not in self._handlers:
                warnings.append(
                    f"Action {i} ({action.action_type.value}): no handler registered"
                )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "event_id": event.id,
        }

    def get_compiled(self, event_id: str) -> Optional["CompiledEvent"]:
        return self._compiled_cache.get(event_id)

    def clear_cache(self) -> None:
        self._compiled_cache.clear()


@dataclass
class CompiledEvent:
    """A compiled event ready for engine execution."""
    event_id: str
    name: str
    conditions: List[Condition]
    actions: List[GameAction]
    priority: int = 0
    last_evaluated: bool = False
    evaluation_count: int = 0


class GameLogicRuntime:
    """
    Runtime executor for compiled game logic.

    Evaluates conditions against the game context and executes
    matching actions. Supports priority ordering, cooldown tracking,
    and trigger limits.
    """

    def __init__(self, compiler: Optional[GameLogicCompiler] = None):
        self._compiler = compiler or GameLogicCompiler()
        self._events: List[GameEvent] = []
        self._compiled: List[CompiledEvent] = []
        self._context: Dict[str, Any] = {}
        self._tick_count: int = 0
        self._triggered_events: List[str] = []
        self._action_log: List[Dict[str, Any]] = []
        self._action_errors: List[Dict[str, Any]] = []

    @property
    def context(self) -> Dict[str, Any]:
        return self._context

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def update_context(self, updates: Dict[str, Any]) -> None:
        self._context.update(updates)

    def add_event(self, event: GameEvent) -> str:
        compiled = self._compiler.compile(event)
        self._events.append(event)
        self._compiled.append(compiled)
        logger.debug("Added event '%s' with %d conditions, %d actions", event.name, len(event.conditions), len(event.actions))
        return event.id

    def remove_event(self, event_id: str) -> bool:
        for i, event in enumerate(self._events):
            if event.id == event_id:
                self._events.pop(i)
                self._compiled.pop(i)
                return True
        return False

    def tick(self, delta_time: float = 0.016) -> List[Dict[str, Any]]:
        """
        Evaluate all events and trigger matching actions.

        For each triggered event, every registered action handler is
        invoked with (action, context). Unregistered action types are
        skipped (logged as orphan). Returns triggered-event summaries
        for auditing.
        """
        self._tick_count += 1
        triggered: List[Dict[str, Any]] = []

        # Sort by priority (higher priority first)
        sorted_events = sorted(
            zip(self._events, self._compiled),
            key=lambda x: x[0].priority,
            reverse=True,
        )

        for event, compiled in sorted_events:
            if event.can_trigger(self._context):
                event.mark_triggered()
                compiled.last_evaluated = True
                compiled.evaluation_count += 1

                triggered.append({
                    "event_id": event.id,
                    "event_name": event.name,
                    "trigger_count": event.trigger_count,
                    "actions": len(event.actions),
                })

                # Invoke registered handlers and log every action for audit
                for action in event.actions:
                    handler = self._compiler._handlers.get(action.action_type)
                    log_entry: Dict[str, Any] = {
                        "tick": self._tick_count,
                        "event_id": event.id,
                        "event_name": event.name,
                        "action_type": action.action_type.value,
                        "target": action.target,
                        "params": dict(action.params),
                        "executed": handler is not None,
                    }
                    if handler is None:
                        log_entry["warning"] = "no handler registered"
                    else:
                        try:
                            handler(action, self._context)
                        except Exception as exc:
                            log_entry["error"] = str(exc)
                            self._action_errors.append(log_entry)
                    self._action_log.append(log_entry)
            else:
                compiled.last_evaluated = False

        self._triggered_events = [t["event_id"] for t in triggered]
        return triggered

    def get_triggered_events(self) -> List[str]:
        return list(self._triggered_events)

    def get_action_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._action_log[-limit:]

    def get_action_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._action_errors[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_events": len(self._events),
            "triggered_last_tick": len(self._triggered_events),
            "total_actions_logged": len(self._action_log),
            "total_action_errors": len(self._action_errors),
            "tick_count": self._tick_count,
            "context_keys": list(self._context.keys()),
            "registered_handlers": [t.value for t in self._compiler._handlers.keys()],
        }

    def export_events(self) -> List[Dict[str, Any]]:
        """Export all events for serialization/transmission."""
        return [e.to_dict() for e in self._events]

    def import_events(self, data: List[Dict[str, Any]]) -> List[str]:
        """Import events from serialized data. Returns imported event IDs."""
        imported = []
        for event_data in data:
            event = GameEvent(
                id=event_data.get("id", uuid.uuid4().hex[:8]),
                name=event_data.get("name", "Imported Event"),
                description=event_data.get("description", ""),
                enabled=event_data.get("enabled", True),
                priority=event_data.get("priority", 0),
            )

            # Rebuild conditions
            for cond_data in event_data.get("conditions", []):
                condition = Condition(
                    id=cond_data.get("id", uuid.uuid4().hex[:8]),
                    operator=ConditionOperator(cond_data.get("operator", "equals")),
                )
                event.conditions.append(condition)

            # Rebuild actions
            for action_data in event_data.get("actions", []):
                action = GameAction(
                    id=action_data.get("id", uuid.uuid4().hex[:8]),
                    action_type=ActionType(action_data.get("action_type", "custom")),
                    target=action_data.get("target", ""),
                    params=action_data.get("params", {}),
                    delay_ms=action_data.get("delay_ms", 0),
                    repeat_count=action_data.get("repeat_count", 1),
                )
                event.actions.append(action)

            self.add_event(event)
            imported.append(event.id)
        return imported


def create_event_from_nl(description: str) -> GameEvent:
    """
    Create a GameEvent from a natural language description.

    Uses keyword heuristics to map NL descriptions to structured
    conditions and actions. This is the bridge between AI-generated
    game logic and the engine's AOT-compiled IR.
    """
    event = GameEvent()

    desc_lower = description.lower()

    # Detect trigger conditions
    if "when" in desc_lower or "if" in desc_lower:
        # Extract the condition part
        for keyword in ["when", "if", "while"]:
            if keyword in desc_lower:
                parts = desc_lower.split(keyword, 1)
                if len(parts) > 1:
                    condition_text = parts[1].split("then")[0].strip() if "then" in desc_lower else parts[1].strip()
                    condition_text = parts[1].split(",")[0].strip() if "," in condition_text else condition_text

                    # Parse common condition patterns
                    if "health" in condition_text and ("below" in condition_text or "less" in condition_text or "<" in condition_text):
                        condition = Condition(
                            left=Expression(type="variable", variable_path="player.health"),
                            operator=ConditionOperator.LESS_THAN,
                            right=Expression(type="literal", value=30),
                        )
                        event.conditions.append(condition)
                    elif "score" in condition_text and ("reaches" in condition_text or "above" in condition_text or ">" in condition_text):
                        condition = Condition(
                            left=Expression(type="variable", variable_path="game.score"),
                            operator=ConditionOperator.GREATER_THAN,
                            right=Expression(type="literal", value=1000),
                        )
                        event.conditions.append(condition)
                    elif "enemy" in condition_text and "near" in condition_text:
                        condition = Condition(
                            left=Expression(type="variable", variable_path="enemy.distance"),
                            operator=ConditionOperator.LESS_THAN,
                            right=Expression(type="literal", value=100),
                        )
                        event.conditions.append(condition)
                    elif "key" in condition_text or "button" in condition_text or "press" in condition_text:
                        condition = Condition(
                            left=Expression(type="variable", variable_path="input.action"),
                            operator=ConditionOperator.EQUALS,
                            right=Expression(type="literal", value="trigger"),
                        )
                        event.conditions.append(condition)
                    break

    # Default condition if none detected
    if not event.conditions:
        condition = Condition(
            left=Expression(type="variable", variable_path="game.tick"),
            operator=ConditionOperator.GREATER_EQUAL,
            right=Expression(type="literal", value=0),
        )
        event.conditions.append(condition)

    # Detect actions
    if "spawn" in desc_lower or "create" in desc_lower or "generate" in desc_lower:
        event.actions.append(GameAction(
            action_type=ActionType.SPAWN_ENTITY,
            target=desc_lower.split("spawn")[-1].strip().split()[0] if "spawn" in desc_lower else "enemy",
            params={"count": 1},
        ))
    if "destroy" in desc_lower or "remove" in desc_lower or "kill" in desc_lower:
        event.actions.append(GameAction(
            action_type=ActionType.DESTROY_ENTITY,
            target="self",
        ))
    if "add score" in desc_lower or "increase score" in desc_lower or "points" in desc_lower:
        event.actions.append(GameAction(
            action_type=ActionType.ADD_SCORE,
            target="game",
            params={"amount": 100},
        ))
    if "play" in desc_lower and ("sound" in desc_lower or "music" in desc_lower or "audio" in desc_lower):
        event.actions.append(GameAction(
            action_type=ActionType.PLAY_SOUND,
            target="self",
            params={"sound_name": "default"},
        ))
    if "damage" in desc_lower or "hit" in desc_lower or "attack" in desc_lower:
        event.actions.append(GameAction(
            action_type=ActionType.DAMAGE_ENTITY,
            target="self",
            params={"amount": 10},
        ))
    if "heal" in desc_lower or "restore" in desc_lower or "recover" in desc_lower:
        event.actions.append(GameAction(
            action_type=ActionType.HEAL_ENTITY,
            target="self",
            params={"amount": 25},
        ))
    if "display" in desc_lower or "show" in desc_lower or "message" in desc_lower or "text" in desc_lower:
        event.actions.append(GameAction(
            action_type=ActionType.DISPLAY_TEXT,
            target="hud",
            params={"text": "Event triggered!"},
        ))
    if "change scene" in desc_lower or "next level" in desc_lower or "transition" in desc_lower:
        event.actions.append(GameAction(
            action_type=ActionType.CHANGE_SCENE,
            target="next_scene",
        ))

    # If no actions detected, add a default
    if not event.actions:
        event.actions.append(GameAction(
            action_type=ActionType.CUSTOM,
            target="self",
            params={"description": description},
        ))

    event.name = description[:50]
    event.description = description

    return event
