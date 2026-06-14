"""
SparkLabs Engine - Event-to-Code Transpilation System

Transpiles visual event sheets (conditions + actions) into executable code
in multiple target languages. Events are the core game logic authoring
paradigm — they describe "when X happens, do Y" rules. This system
converts those declarative rules into well-structured, commented source
code that can be executed directly in the target runtime.

Architecture:
  EngineEventCodegen (Singleton)
    |-- EventSheet          — container of events, variables, and metadata
    |-- GameEvent           — single condition→actions rule with sub-events
    |-- EventCondition      — trigger predicate (collision, timer, input, etc.)
    |-- EventAction         — executable operation (move, spawn, play_sound, etc.)
    |-- GeneratedCode       — output of transpilation (language, source, deps)
    |-- CodeTemplate        — pre-built event patterns for common game logic
    |-- ValidationResult    — logical consistency check outcome
    |-- OptimizationReport  — merge/reorder/removal statistics

Code Generation Pipeline:
  1. Parse event sheet into intermediate representation
  2. Validate events for logical consistency
  3. Optimize event ordering and merge compatible events
  4. Emit target-language source with header comments and imports
  5. Return GeneratedCode with entry point and dependency list

Supported Languages:
  - Python  (generate_python)
  - JavaScript (generate_javascript)
  - Lua      (generate_lua)

Event Templates:
  - PLATFORMER_MOVEMENT  — horizontal input + jump + gravity
  - COLLISION_RESPONSE   — overlap detection + bounce/collect
  - TIMER_SPAWNING       — interval-based object creation
  - UI_BUTTON_HANDLING   — hover/click/press state transitions
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConditionType(Enum):
    """Types of conditions that can be evaluated against game state."""
    COLLISION = "collision"
    COMPARISON = "comparison"
    TIMER = "timer"
    INPUT = "input"
    VARIABLE = "variable"
    OBJECT_COUNT = "object_count"
    SCENE_STATE = "scene_state"
    RANDOM = "random"
    EXPRESSION = "expression"
    ALWAYS = "always"
    DISTANCE = "distance"
    ANIMATION_STATE = "animation_state"
    CUSTOM = "custom"


class ActionType(Enum):
    """Types of executable actions that modify game state."""
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"
    CREATE = "create"
    DESTROY = "destroy"
    PLAY_SOUND = "play_sound"
    CHANGE_SCENE = "change_scene"
    SET_VARIABLE = "set_variable"
    SPAWN = "spawn"
    APPLY_FORCE = "apply_force"
    PLAY_ANIMATION = "play_animation"
    TRIGGER_EVENT = "trigger_event"
    WAIT = "wait"
    CALL_FUNCTION = "call_function"
    SET_POSITION = "set_position"
    TOGGLE = "toggle"
    CUSTOM = "custom"


class TargetLanguage(Enum):
    """Target programming languages for code generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    LUA = "lua"
    CPP = "cpp"


class ComparisonOperator(Enum):
    """Comparison operators used in condition evaluation."""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER = "greater"
    LESS = "less"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BETWEEN = "between"
    CONTAINS = "contains"


# ---------------------------------------------------------------------------
# Operator symbols for code generation
# ---------------------------------------------------------------------------

_OPERATOR_SYMBOLS: Dict[ComparisonOperator, str] = {
    ComparisonOperator.EQUAL: "==",
    ComparisonOperator.NOT_EQUAL: "!=",
    ComparisonOperator.GREATER: ">",
    ComparisonOperator.LESS: "<",
    ComparisonOperator.GREATER_EQUAL: ">=",
    ComparisonOperator.LESS_EQUAL: "<=",
    ComparisonOperator.BETWEEN: "between",
    ComparisonOperator.CONTAINS: "contains",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EventCondition:
    """A predicate that evaluates to True or False against current game state.

    Each condition has a type (collision, timer, input, etc.), a target object
    to evaluate against, and a dict of parameters specific to the condition type.
    The inverted flag negates the result.
    """

    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    condition_type: ConditionType = ConditionType.ALWAYS
    target_object: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    inverted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "condition_type": self.condition_type.value,
            "target_object": self.target_object,
            "parameters": self.parameters,
            "inverted": self.inverted,
            "metadata": self.metadata,
        }


@dataclass
class EventAction:
    """An executable operation that modifies game state when triggered.

    Each action has a type (move, spawn, play_sound, etc.), a target object
    to operate on, and a dict of parameters specific to the action type.
    """

    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_type: ActionType = ActionType.CUSTOM
    target_object: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "target_object": self.target_object,
            "parameters": self.parameters,
            "metadata": self.metadata,
        }


@dataclass
class GameEvent:
    """A single condition→actions rule with optional sub-events.

    When all conditions evaluate to True, all actions are executed in order.
    Sub-events are evaluated only when the parent event is active.
    The once_trigger flag ensures the event fires at most once.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    conditions: List[EventCondition] = field(default_factory=list)
    actions: List[EventAction] = field(default_factory=list)
    sub_events: List[GameEvent] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    once_trigger: bool = False
    comment: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "sub_events": [se.to_dict() for se in self.sub_events],
            "enabled": self.enabled,
            "priority": self.priority,
            "once_trigger": self.once_trigger,
            "comment": self.comment,
        }


@dataclass
class EventSheet:
    """A named container of game events with scoped variables and metadata.

    An event sheet represents a complete unit of game logic — e.g., player
    controls, enemy AI, or UI interactions. All events within a sheet are
    evaluated in priority order each frame.
    """

    sheet_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    events: List[GameEvent] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_id": self.sheet_id,
            "name": self.name,
            "events": [e.to_dict() for e in self.events],
            "variables": self.variables,
            "metadata": self.metadata,
        }


@dataclass
class GeneratedCode:
    """Output of transpilation: source code in a target language.

    Contains the complete code string, the entry point function name,
    any external dependencies needed, and timing metadata.
    """

    code_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    language: TargetLanguage = TargetLanguage.PYTHON
    source_sheet_id: str = ""
    code_content: str = ""
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code_id": self.code_id,
            "language": self.language.value,
            "source_sheet_id": self.source_sheet_id,
            "code_content": self.code_content,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "timestamp": self.timestamp,
        }


@dataclass
class CodeTemplate:
    """A pre-built event pattern for common game logic scenarios.

    Templates contain placeholder slots that are filled in when applied
    to a sheet, enabling rapid authoring of standard behaviors.
    """

    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    language: TargetLanguage = TargetLanguage.PYTHON
    template_code: str = ""
    parameter_slots: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "language": self.language.value,
            "template_code": self.template_code,
            "parameter_slots": self.parameter_slots,
            "description": self.description,
        }


@dataclass
class ValidationResult:
    """Outcome of checking an event sheet for logical consistency.

    Contains lists of errors (hard failures), warnings (potential issues),
    and suggestions (improvement hints), along with the event that triggered
    each issue.
    """

    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    event_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "event_id": self.event_id,
        }


@dataclass
class OptimizationReport:
    """Statistics describing the outcome of an event sheet optimization pass.

    Tracks how many events were merged, reordered, or removed, and provides
    the overall reduction in event count.
    """

    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    original_count: int = 0
    optimized_count: int = 0
    merges: int = 0
    reorders: int = 0
    removed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "original_count": self.original_count,
            "optimized_count": self.optimized_count,
            "merges": self.merges,
            "reorders": self.reorders,
            "removed": self.removed,
        }


# ---------------------------------------------------------------------------
# EngineEventCodegen — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class EngineEventCodegen:
    """Event-to-code transpilation system for the SparkLabs framework.

    Converts visual event sheets (conditions + actions) into executable code
    in Python, JavaScript, and Lua. Provides event validation, optimization,
    and pre-built templates for common game logic patterns.

    Usage:
        cg = get_engine_event_codegen()
        sheet = cg.create_event_sheet("player_controls")
        cg.add_event(sheet.sheet_id, "move_left", [
            cg.add_condition(cg.create_event_id(), ConditionType.INPUT,
                "player", {"key": "left", "pressed": True})
        ], [
            cg.add_action(cg.create_event_id(), ActionType.MOVE,
                "player", {"x": -5, "y": 0})
        ])
        code = cg.generate_python(sheet.sheet_id)
    """

    _instance: Optional["EngineEventCodegen"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SHEETS = 256
    MAX_EVENTS_PER_SHEET = 512
    MAX_CONDITIONS_PER_EVENT = 32
    MAX_ACTIONS_PER_EVENT = 64

    def __new__(cls) -> "EngineEventCodegen":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._sheets: Dict[str, EventSheet] = {}
        self._generated_code: Dict[str, GeneratedCode] = {}
        self._templates: Dict[str, CodeTemplate] = {}
        self._generation_count: int = 0
        self._total_generation_time: float = 0.0
        self._init_templates()

    @classmethod
    def get_instance(cls) -> "EngineEventCodegen":
        """Thread-safe singleton accessor with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Template initialization
    # ------------------------------------------------------------------

    def _init_templates(self) -> None:
        """Initialize the built-in code templates for common game patterns."""
        self._templates["PLATFORMER_MOVEMENT"] = CodeTemplate(
            template_id="tpl_platformer",
            name="Platformer Movement",
            language=TargetLanguage.PYTHON,
            template_code=(
                "# Platformer movement for {object_name}\n"
                "def {object_name}_movement(dt, input_state, physics):\n"
                "    # Horizontal movement\n"
                "    if input_state.get('left'):\n"
                "        physics.set_velocity_x({object_name}, -{move_speed})\n"
                "    elif input_state.get('right'):\n"
                "        physics.set_velocity_x({object_name}, {move_speed})\n"
                "    else:\n"
                "        physics.set_velocity_x({object_name}, 0)\n"
                "    # Jump\n"
                "    if input_state.get('jump') and physics.is_on_ground({object_name}):\n"
                "        physics.set_velocity_y({object_name}, -{jump_force})\n"
            ),
            parameter_slots={
                "object_name": "player", "move_speed": 200, "jump_force": 400,
            },
            description="Standard platformer movement with horizontal input and jump",
        )

        self._templates["COLLISION_RESPONSE"] = CodeTemplate(
            template_id="tpl_collision",
            name="Collision Response",
            language=TargetLanguage.PYTHON,
            template_code=(
                "# Collision response handler\n"
                "def on_collision(obj_a, obj_b):\n"
                "    # Check collision pair\n"
                "    if obj_a.tag == '{tag_a}' and obj_b.tag == '{tag_b}':\n"
                "        {action_body}\n"
            ),
            parameter_slots={
                "tag_a": "player", "tag_b": "enemy",
                "action_body": "obj_a.take_damage(10); obj_b.destroy()",
            },
            description="Collision detection and response between two object types",
        )

        self._templates["TIMER_SPAWNING"] = CodeTemplate(
            template_id="tpl_timer_spawn",
            name="Timer-Based Spawning",
            language=TargetLanguage.PYTHON,
            template_code=(
                "# Timer-based spawner\n"
                "def spawn_system(dt):\n"
                "    spawn_system._timer += dt\n"
                "    if spawn_system._timer >= {interval}:\n"
                "        spawn_system._timer = 0.0\n"
                "        spawn('{prefab_name}', {spawn_x}, {spawn_y})\n"
                "spawn_system._timer = 0.0\n"
            ),
            parameter_slots={
                "interval": 2.0, "prefab_name": "EnemyBasic",
                "spawn_x": 0, "spawn_y": 0,
            },
            description="Timer-based spawning at a fixed interval",
        )

        self._templates["UI_BUTTON_HANDLING"] = CodeTemplate(
            template_id="tpl_ui_button",
            name="UI Button Handling",
            language=TargetLanguage.PYTHON,
            template_code=(
                "# UI Button state machine\n"
                "def update_{button_id}(mouse_x, mouse_y, mouse_pressed):\n"
                "    hover = point_in_rect(mouse_x, mouse_y, {rect_x}, {rect_y}, {rect_w}, {rect_h})\n"
                "    if hover and mouse_pressed:\n"
                "        set_button_state('{button_id}', 'pressed')\n"
                "        {on_click_handler}()\n"
                "    elif hover:\n"
                "        set_button_state('{button_id}', 'hover')\n"
                "    else:\n"
                "        set_button_state('{button_id}', 'default')\n"
            ),
            parameter_slots={
                "button_id": "start_button", "rect_x": 100, "rect_y": 200,
                "rect_w": 200, "rect_h": 60, "on_click_handler": "start_game",
            },
            description="UI button with hover, pressed, and default states",
        )

    # ------------------------------------------------------------------
    # Event Sheet Management
    # ------------------------------------------------------------------

    def create_event_sheet(self, name: str) -> EventSheet:
        """Create a new event sheet for organizing game logic events.

        Args:
            name: Human-readable name for the sheet.

        Returns:
            New EventSheet instance registered in the codegen system.
        """
        if len(self._sheets) >= self.MAX_SHEETS:
            raise RuntimeError(
                f"Maximum number of event sheets ({self.MAX_SHEETS}) reached"
            )
        sheet = EventSheet(
            sheet_id=uuid.uuid4().hex,
            name=name,
            metadata={"created_at": _time_module.time()},
        )
        self._sheets[sheet.sheet_id] = sheet
        return sheet

    def add_event(
        self,
        sheet_id: str,
        event_name: str,
        conditions: List[EventCondition],
        actions: List[EventAction],
    ) -> Optional[GameEvent]:
        """Add an event (condition→actions rule) to an event sheet.

        Args:
            sheet_id: ID of the target event sheet.
            event_name: Human-readable name for the event.
            conditions: List of conditions that must all be True.
            actions: List of actions to execute when conditions are met.

        Returns:
            The new GameEvent, or None if the sheet was not found or is full.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        if len(sheet.events) >= self.MAX_EVENTS_PER_SHEET:
            return None
        event = GameEvent(
            event_id=uuid.uuid4().hex,
            name=event_name,
            conditions=conditions,
            actions=actions,
        )
        sheet.events.append(event)
        return event

    def add_condition(
        self,
        event_id: str,
        condition_type: ConditionType,
        target_object: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> EventCondition:
        """Create an EventCondition to be used when building events.

        This is a factory method; the returned condition is not automatically
        attached to any event. Pass it to add_event() in the conditions list.

        Args:
            event_id: ID of the owning event (for metadata tracking).
            condition_type: The type of condition.
            target_object: Object to evaluate the condition against.
            parameters: Type-specific parameters (e.g., key, value, operator).

        Returns:
            A new EventCondition instance.
        """
        return EventCondition(
            condition_id=uuid.uuid4().hex,
            condition_type=condition_type,
            target_object=target_object,
            parameters=parameters or {},
            metadata={"event_id": event_id},
        )

    def add_action(
        self,
        event_id: str,
        action_type: ActionType,
        target_object: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> EventAction:
        """Create an EventAction to be used when building events.

        This is a factory method; the returned action is not automatically
        attached to any event. Pass it to add_event() in the actions list.

        Args:
            event_id: ID of the owning event (for metadata tracking).
            action_type: The type of action.
            target_object: Object to perform the action on.
            parameters: Type-specific parameters (e.g., x, y, speed, sound_id).

        Returns:
            A new EventAction instance.
        """
        return EventAction(
            action_id=uuid.uuid4().hex,
            action_type=action_type,
            target_object=target_object,
            parameters=parameters or {},
            metadata={"event_id": event_id},
        )

    def get_event_sheet(self, sheet_id: str) -> Optional[EventSheet]:
        """Retrieve an event sheet by its ID."""
        return self._sheets.get(sheet_id)

    def list_sheets(self) -> List[Dict[str, Any]]:
        """List all event sheets with summary metadata."""
        return [
            {
                "sheet_id": s.sheet_id,
                "name": s.name,
                "event_count": len(s.events),
                "metadata": s.metadata,
            }
            for s in self._sheets.values()
        ]

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available code templates with their descriptions."""
        return [
            {
                "template_id": t.template_id,
                "name": t.name,
                "language": t.language.value,
                "description": t.description,
                "parameter_slots": list(t.parameter_slots.keys()),
            }
            for t in self._templates.values()
        ]

    # ------------------------------------------------------------------
    # Event Validation
    # ------------------------------------------------------------------

    def validate_sheet(self, sheet_id: str) -> Optional[ValidationResult]:
        """Validate an event sheet for logical consistency.

        Checks for:
          - Unreachable events (conditions that can never be True, e.g., ALWAYS
            before a condition that checks a variable that is only set after).
          - Circular dependencies (events that trigger each other).
          - Missing targets (actions referencing objects not defined in the sheet).
          - Events with no conditions (always-fire, which may be intentional).
          - Events with no actions (dead events that do nothing).

        Args:
            sheet_id: ID of the event sheet to validate.

        Returns:
            ValidationResult with errors, warnings, and suggestions.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None

        errors: List[str] = []
        warnings: List[str] = []
        suggestions: List[str] = []

        all_object_names: Set[str] = set()
        triggered_events: Set[str] = set()
        event_names: Set[str] = set()

        for event in sheet.events:
            event_names.add(event.name)

            # Check for empty conditions
            if not event.conditions:
                warnings.append(
                    f"Event '{event.name}' has no conditions — will fire every frame"
                )

            # Check for empty actions
            if not event.actions:
                warnings.append(
                    f"Event '{event.name}' has no actions — dead event"
                )

            # Collect target objects from conditions
            for cond in event.conditions:
                if cond.target_object:
                    all_object_names.add(cond.target_object)

            # Collect target objects and triggered events from actions
            for action in event.actions:
                if action.target_object:
                    all_object_names.add(action.target_object)
                if action.action_type == ActionType.TRIGGER_EVENT:
                    tgt = action.parameters.get("event_name", "")
                    if tgt:
                        triggered_events.add(tgt)

        # Check circular dependencies
        for event in sheet.events:
            for action in event.actions:
                if action.action_type == ActionType.TRIGGER_EVENT:
                    tgt_name = action.parameters.get("event_name", "")
                    if tgt_name == event.name:
                        warnings.append(
                            f"Event '{event.name}' triggers itself — potential infinite loop"
                        )
                    elif tgt_name and tgt_name not in event_names:
                        warnings.append(
                            f"Event '{event.name}' triggers unknown event '{tgt_name}'"
                        )

        # Check for unreachable events (events after an ALWAYS condition with
        # higher priority that would prevent them from being evaluated)
        always_events = [e for e in sheet.events
                         if any(c.condition_type == ConditionType.ALWAYS
                                for c in e.conditions)]
        if always_events:
            suggestions.append(
                "Sheet contains ALWAYS events — ensure they do not shadow "
                "lower-priority events"
            )

        # Check for missing targets
        referenced_in_actions = set()
        for event in sheet.events:
            for action in event.actions:
                if action.target_object:
                    referenced_in_actions.add(action.target_object)
        for target in referenced_in_actions:
            if target not in all_object_names:
                suggestions.append(
                    f"Action target '{target}' is not referenced in any condition "
                    "— verify it exists at runtime"
                )

        valid = len(errors) == 0

        return ValidationResult(
            result_id=uuid.uuid4().hex,
            valid=valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            event_id=sheet_id,
        )

    # ------------------------------------------------------------------
    # Event Optimization
    # ------------------------------------------------------------------

    def optimize_sheet(self, sheet_id: str) -> Optional[OptimizationReport]:
        """Optimize an event sheet by merging, reordering, and pruning events.

        Optimization passes:
          1. Remove redundant checks — events with identical conditions are
             merged into a single event with combined actions.
          2. Reorder by priority — events with higher priority are evaluated
             first to allow early exits.
          3. Remove disabled events — events with enabled=False are pruned.

        Args:
            sheet_id: ID of the event sheet to optimize.

        Returns:
            OptimizationReport with before/after statistics.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None

        original_count = len(sheet.events)
        merges = 0
        removed = 0

        # Remove disabled events
        active_events = [e for e in sheet.events if e.enabled]
        removed += (original_count - len(active_events))

        # Merge events with identical conditions
        merged_events: List[GameEvent] = []
        seen_condition_sigs: Dict[str, GameEvent] = {}

        for event in active_events:
            sig = self._condition_signature(event)
            if sig in seen_condition_sigs:
                # Merge actions into the existing event
                seen_condition_sigs[sig].actions.extend(event.actions)
                merges += 1
            else:
                seen_condition_sigs[sig] = event
                merged_events.append(event)

        # Reorder by priority (descending)
        merged_events.sort(key=lambda e: e.priority, reverse=True)

        sheet.events = merged_events
        optimized_count = len(sheet.events)

        return OptimizationReport(
            report_id=uuid.uuid4().hex,
            original_count=original_count,
            optimized_count=optimized_count,
            merges=merges,
            reorders=1 if original_count > 1 else 0,
            removed=removed,
        )

    def _condition_signature(self, event: GameEvent) -> str:
        """Generate a stable signature string for an event's conditions.

        Used to detect events with identical conditions for merging.
        """
        parts = []
        for c in sorted(event.conditions, key=lambda x: x.condition_type.value):
            parts.append(
                f"{c.condition_type.value}|{c.target_object}|"
                f"{sorted(c.parameters.items())}|{c.inverted}"
            )
        return "||".join(parts)

    # ------------------------------------------------------------------
    # Code Generation — Python
    # ------------------------------------------------------------------

    def generate_code(
        self,
        sheet_id: str,
        target_language: TargetLanguage,
    ) -> Optional[GeneratedCode]:
        """Generate executable code from an event sheet in the target language.

        Dispatches to the appropriate language-specific generator.

        Args:
            sheet_id: ID of the event sheet to transpile.
            target_language: Target programming language.

        Returns:
            GeneratedCode with the complete source, entry point, and dependencies.
        """
        if target_language == TargetLanguage.PYTHON:
            return self.generate_python(sheet_id)
        elif target_language == TargetLanguage.JAVASCRIPT:
            return self.generate_javascript(sheet_id)
        elif target_language == TargetLanguage.LUA:
            return self.generate_lua(sheet_id)
        else:
            return None

    def generate_python(self, sheet_id: str) -> Optional[GeneratedCode]:
        """Generate Python source code from an event sheet.

        Produces a self-contained Python module with an evaluate_sheet()
        function that accepts game state and returns a list of actions.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None

        start_time = _time_module.time()
        lines: List[str] = []

        # Header
        lines.append('"""')
        lines.append(f"Auto-generated event sheet: {sheet.name}")
        lines.append(f"Generated by SparkLabs EngineEventCodegen")
        lines.append(f"Sheet ID: {sheet.sheet_id}")
        lines.append(f"Events: {len(sheet.events)}")
        lines.append('"""')
        lines.append("")
        lines.append("from typing import Any, Dict, List, Optional")
        lines.append("import math")
        lines.append("")
        lines.append("")

        # Variable declarations
        lines.append("# ---- Sheet Variables ----")
        for var_name, var_value in sheet.variables.items():
            lines.append(f"{var_name} = {repr(var_value)}")
        lines.append("")
        lines.append("")

        # Condition evaluator helpers
        lines.append("# ---- Condition Evaluators ----")
        lines.append("")
        lines.append("def _compare(a, op: str, b) -> bool:")
        lines.append('    """Evaluate a comparison between two values."""')
        lines.append("    if op == 'equal':")
        lines.append("        return a == b")
        lines.append("    elif op == 'not_equal':")
        lines.append("        return a != b")
        lines.append("    elif op == 'greater':")
        lines.append("        return float(a) > float(b)")
        lines.append("    elif op == 'less':")
        lines.append("        return float(a) < float(b)")
        lines.append("    elif op == 'greater_equal':")
        lines.append("        return float(a) >= float(b)")
        lines.append("    elif op == 'less_equal':")
        lines.append("        return float(a) <= float(b)")
        lines.append("    elif op == 'between':")
        lines.append("        if isinstance(b, (list, tuple)) and len(b) >= 2:")
        lines.append("            return b[0] <= a <= b[1]")
        lines.append("        return False")
        lines.append("    elif op == 'contains':")
        lines.append("        return str(b) in str(a) if a is not None else False")
        lines.append("    return False")
        lines.append("")
        lines.append("")

        # Per-event condition functions
        lines.append("# ---- Event Condition Functions ----")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            func_name = f"_check_event_{idx}_{_sanitize_name(event.name)}"
            lines.append(f"def {func_name}(state: Dict[str, Any]) -> bool:")
            lines.append(f'    """{event.name}"""')
            if not event.conditions:
                lines.append("    return True  # Always-fires event")
            else:
                lines.append("    # All conditions must be True")
                for cond in event.conditions:
                    cond_line = self._emit_python_condition(cond)
                    lines.append(f"    {cond_line}")
                lines.append("    return True")
            lines.append("")
            lines.append("")

        # Per-event action functions
        lines.append("# ---- Event Action Functions ----")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            func_name = f"_execute_event_{idx}_{_sanitize_name(event.name)}"
            lines.append(
                f"def {func_name}(state: Dict[str, Any], "
                f"dispatch: Any) -> List[Dict[str, Any]]:"
            )
            lines.append(f'    """Execute actions for: {event.name}"""')
            lines.append("    results = []")
            for action in event.actions:
                action_lines = self._emit_python_action(action)
                for al in action_lines:
                    lines.append(f"    {al}")
            lines.append("    return results")
            lines.append("")
            lines.append("")

        # Sub-event evaluators
        for idx, event in enumerate(sheet.events):
            if not event.enabled or not event.sub_events:
                continue
            parent_func = f"_check_event_{idx}_{_sanitize_name(event.name)}"
            lines.append(f"# ---- Sub-events for {event.name} ----")
            for sidx, sub in enumerate(event.sub_events):
                if not sub.enabled:
                    continue
                func_name = (
                    f"_check_sub_event_{idx}_{sidx}_"
                    f"{_sanitize_name(sub.name)}"
                )
                lines.append(f"def {func_name}(state: Dict[str, Any]) -> bool:")
                lines.append(f'    """Sub-event: {sub.name}"""')
                if not sub.conditions:
                    lines.append("    return True")
                else:
                    for cond in sub.conditions:
                        cond_line = self._emit_python_condition(cond)
                        lines.append(f"    {cond_line}")
                    lines.append("    return True")
                lines.append("")
                lines.append("")

        # Main evaluation loop
        lines.append("# ---- Main Evaluation Loop ----")
        lines.append("")
        lines.append("def evaluate_sheet(state: Dict[str, Any]) -> List[Dict[str, Any]]:")
        lines.append(f'    """Evaluate all events in sheet: {sheet.name}')
        lines.append("")
        lines.append("    Args:")
        lines.append("        state: Game state dictionary with object properties.")
        lines.append("")
        lines.append("    Returns:")
        lines.append("        List of action results (dicts with action metadata).")
        lines.append('    """')
        lines.append("    all_results = []")
        lines.append("")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            check_func = f"_check_event_{idx}_{_sanitize_name(event.name)}"
            exec_func = f"_execute_event_{idx}_{_sanitize_name(event.name)}"
            lines.append(f"    # Event {idx}: {event.name}")
            if event.once_trigger:
                lines.append(
                    f"    if not state.get('_event_{idx}_fired', False) "
                    f"and {check_func}(state):"
                )
                lines.append(f"        state['_event_{idx}_fired'] = True")
                lines.append(f"        all_results.extend({exec_func}(state, None))")
            else:
                lines.append(f"    if {check_func}(state):")
                lines.append(f"        all_results.extend({exec_func}(state, None))")
            # Sub-events
            for sidx, sub in enumerate(event.sub_events):
                if not sub.enabled:
                    continue
                sub_check = (
                    f"_check_sub_event_{idx}_{sidx}_"
                    f"{_sanitize_name(sub.name)}"
                )
                lines.append(f"        # Sub-event: {sub.name}")
                lines.append(f"        if {sub_check}(state):")
                for sa in sub.actions:
                    sub_lines = self._emit_python_action(sa)
                    for sl in sub_lines:
                        lines.append(f"            {sl}")
            lines.append("")
        lines.append("    return all_results")
        lines.append("")

        code_content = "\n".join(lines)
        self._generation_count += 1
        elapsed = _time_module.time() - start_time
        self._total_generation_time += elapsed

        generated = GeneratedCode(
            code_id=uuid.uuid4().hex,
            language=TargetLanguage.PYTHON,
            source_sheet_id=sheet_id,
            code_content=code_content,
            entry_point="evaluate_sheet",
            dependencies=[],
            timestamp=_time_module.time(),
        )
        self._generated_code[generated.code_id] = generated
        return generated

    def _emit_python_condition(self, cond: EventCondition) -> str:
        """Emit Python code for a single condition."""
        params = cond.parameters
        prefix = "not " if cond.inverted else ""
        negate = "not " if cond.inverted else ""

        if cond.condition_type == ConditionType.ALWAYS:
            return "if True:  # Always-fires"
        elif cond.condition_type == ConditionType.COLLISION:
            obj_a = cond.target_object
            obj_b = params.get("with_object", "")
            return (
                f"if {negate}state.get('collisions', {{}}).get("
                f"'{obj_a}', '') == '{obj_b}': return False"
            )
        elif cond.condition_type == ConditionType.COMPARISON:
            obj = cond.target_object
            prop = params.get("property", "value")
            op = params.get("operator", "equal")
            val = params.get("value", 0)
            return (
                f"if {negate}_compare(state.get('{obj}', {{}}).get('{prop}', 0), "
                f"'{op}', {repr(val)}): return False"
            )
        elif cond.condition_type == ConditionType.TIMER:
            timer_name = params.get("timer_name", cond.target_object)
            threshold = params.get("threshold", 1.0)
            return (
                f"if {negate}state.get('timers', {{}}).get('{timer_name}', 0) "
                f"< {threshold}: return False"
            )
        elif cond.condition_type == ConditionType.INPUT:
            key = params.get("key", "")
            pressed = params.get("pressed", True)
            if pressed:
                return (
                    f"if {negate}state.get('input', {{}}).get('{key}', {{}})"
                    f".get('pressed', False): return False"
                )
            else:
                return (
                    f"if {negate}not state.get('input', {{}}).get('{key}', {{}})"
                    f".get('pressed', False): return False"
                )
        elif cond.condition_type == ConditionType.VARIABLE:
            var_name = params.get("variable_name", "")
            op = params.get("operator", "equal")
            val = params.get("value", 0)
            return (
                f"if {negate}_compare(state.get('variables', {{}})."
                f"get('{var_name}', 0), '{op}', {repr(val)}): return False"
            )
        elif cond.condition_type == ConditionType.OBJECT_COUNT:
            obj_type = params.get("object_type", cond.target_object)
            op = params.get("operator", "greater")
            count = params.get("count", 0)
            return (
                f"if {negate}_compare(len(state.get('objects', {{}})."
                f"get('{obj_type}', [])), '{op}', {count}): return False"
            )
        elif cond.condition_type == ConditionType.SCENE_STATE:
            scene_name = params.get("scene_name", "")
            return (
                f"if {negate}state.get('current_scene', '') == "
                f"'{scene_name}': return False"
            )
        elif cond.condition_type == ConditionType.RANDOM:
            probability = params.get("probability", 0.5)
            return (
                f"if {negate}__import__('random').random() < "
                f"{probability}: return False"
            )
        elif cond.condition_type == ConditionType.EXPRESSION:
            expr = params.get("expression", "True")
            return f"if {negate}({expr}): return False"
        elif cond.condition_type == ConditionType.DISTANCE:
            obj_a = cond.target_object
            obj_b = params.get("to_object", "")
            op = params.get("operator", "less")
            dist = params.get("distance", 100)
            return (
                f"if {negate}_compare("
                f"math.hypot("
                f"state.get('{obj_a}', {{}}).get('x', 0) - "
                f"state.get('{obj_b}', {{}}).get('x', 0), "
                f"state.get('{obj_a}', {{}}).get('y', 0) - "
                f"state.get('{obj_b}', {{}}).get('y', 0)),"
                f" '{op}', {dist}): return False"
            )
        elif cond.condition_type == ConditionType.ANIMATION_STATE:
            obj = cond.target_object
            anim = params.get("animation_name", "")
            return (
                f"if {negate}state.get('{obj}', {{}}).get('animation', '') "
                f"== '{anim}': return False"
            )
        elif cond.condition_type == ConditionType.CUSTOM:
            func_name = params.get("function_name", "custom_check")
            return f"if {negate}{func_name}(state): return False"
        return "if True:  # Unknown condition"

    def _emit_python_action(self, action: EventAction) -> List[str]:
        """Emit Python code lines for a single action."""
        params = action.parameters
        results: List[str] = []

        if action.action_type == ActionType.MOVE:
            dx = params.get("x", 0)
            dy = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"obj = state.get('{obj}', {{}}); "
                f"obj['x'] = obj.get('x', 0) + {dx}; "
                f"obj['y'] = obj.get('y', 0) + {dy}"
            )
            results.append(
                f"results.append({{'action': 'move', 'target': '{obj}', "
                f"'dx': {dx}, 'dy': {dy}}})"
            )
        elif action.action_type == ActionType.ROTATE:
            angle = params.get("angle", 0)
            obj = action.target_object
            results.append(
                f"obj = state.get('{obj}', {{}}); "
                f"obj['rotation'] = obj.get('rotation', 0) + {angle}"
            )
            results.append(
                f"results.append({{'action': 'rotate', 'target': '{obj}', "
                f"'angle': {angle}}})"
            )
        elif action.action_type == ActionType.SCALE:
            sx = params.get("x", 1.0)
            sy = params.get("y", 1.0)
            obj = action.target_object
            results.append(
                f"obj = state.get('{obj}', {{}}); "
                f"obj['scale_x'] = obj.get('scale_x', 1.0) * {sx}; "
                f"obj['scale_y'] = obj.get('scale_y', 1.0) * {sy}"
            )
            results.append(
                f"results.append({{'action': 'scale', 'target': '{obj}', "
                f"'sx': {sx}, 'sy': {sy}}})"
            )
        elif action.action_type == ActionType.CREATE:
            obj_type = params.get("object_type", action.target_object)
            x = params.get("x", 0)
            y = params.get("y", 0)
            results.append(
                f"state.setdefault('objects', {{}}).setdefault('{obj_type}', [])"
                f".append({{'x': {x}, 'y': {y}, 'type': '{obj_type}'}})"
            )
            results.append(
                f"results.append({{'action': 'create', 'type': '{obj_type}', "
                f"'x': {x}, 'y': {y}}})"
            )
        elif action.action_type == ActionType.DESTROY:
            obj = action.target_object
            results.append(f"state.pop('{obj}', None)")
            results.append(
                f"results.append({{'action': 'destroy', 'target': '{obj}'}})"
            )
        elif action.action_type == ActionType.PLAY_SOUND:
            sound_id = params.get("sound_id", "")
            volume = params.get("volume", 1.0)
            results.append(
                f"results.append({{'action': 'play_sound', "
                f"'sound_id': '{sound_id}', 'volume': {volume}}})"
            )
        elif action.action_type == ActionType.CHANGE_SCENE:
            scene_name = params.get("scene_name", "")
            results.append(
                f"state['current_scene'] = '{scene_name}'"
            )
            results.append(
                f"results.append({{'action': 'change_scene', "
                f"'scene': '{scene_name}'}})"
            )
        elif action.action_type == ActionType.SET_VARIABLE:
            var_name = params.get("variable_name", "")
            value = params.get("value", 0)
            results.append(
                f"state.setdefault('variables', {{}})['{var_name}'] = {repr(value)}"
            )
            results.append(
                f"results.append({{'action': 'set_variable', "
                f"'name': '{var_name}', 'value': {repr(value)}}})"
            )
        elif action.action_type == ActionType.SPAWN:
            prefab = params.get("prefab_name", action.target_object)
            x = params.get("x", 0)
            y = params.get("y", 0)
            results.append(
                f"state.setdefault('objects', {{}}).setdefault('{prefab}', [])"
                f".append({{'x': {x}, 'y': {y}, 'prefab': '{prefab}'}})"
            )
            results.append(
                f"results.append({{'action': 'spawn', 'prefab': '{prefab}', "
                f"'x': {x}, 'y': {y}}})"
            )
        elif action.action_type == ActionType.APPLY_FORCE:
            fx = params.get("x", 0)
            fy = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"obj = state.get('{obj}', {{}}); "
                f"obj['vx'] = obj.get('vx', 0) + {fx}; "
                f"obj['vy'] = obj.get('vy', 0) + {fy}"
            )
            results.append(
                f"results.append({{'action': 'apply_force', 'target': '{obj}', "
                f"'fx': {fx}, 'fy': {fy}}})"
            )
        elif action.action_type == ActionType.PLAY_ANIMATION:
            anim_name = params.get("animation_name", "")
            obj = action.target_object
            results.append(
                f"state.get('{obj}', {{}})['animation'] = '{anim_name}'"
            )
            results.append(
                f"results.append({{'action': 'play_animation', 'target': '{obj}', "
                f"'animation': '{anim_name}'}})"
            )
        elif action.action_type == ActionType.TRIGGER_EVENT:
            event_name = params.get("event_name", "")
            results.append(
                f"results.append({{'action': 'trigger_event', "
                f"'event': '{event_name}'}})"
            )
        elif action.action_type == ActionType.WAIT:
            duration = params.get("duration", 0.0)
            results.append(
                f"results.append({{'action': 'wait', "
                f"'duration': {duration}}})"
            )
        elif action.action_type == ActionType.CALL_FUNCTION:
            func_name = params.get("function_name", "")
            func_args = params.get("arguments", [])
            results.append(
                f"results.append({{'action': 'call_function', "
                f"'function': '{func_name}', 'args': {func_args}}})"
            )
        elif action.action_type == ActionType.SET_POSITION:
            x = params.get("x", 0)
            y = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"obj = state.get('{obj}', {{}}); "
                f"obj['x'] = {x}; obj['y'] = {y}"
            )
            results.append(
                f"results.append({{'action': 'set_position', 'target': '{obj}', "
                f"'x': {x}, 'y': {y}}})"
            )
        elif action.action_type == ActionType.TOGGLE:
            prop = params.get("property", "enabled")
            obj = action.target_object
            results.append(
                f"obj = state.get('{obj}', {{}}); "
                f"obj['{prop}'] = not obj.get('{prop}', False)"
            )
            results.append(
                f"results.append({{'action': 'toggle', 'target': '{obj}', "
                f"'property': '{prop}'}})"
            )
        elif action.action_type == ActionType.CUSTOM:
            func_name = params.get("function_name", "custom_action")
            results.append(
                f"results.append({{'action': 'custom', "
                f"'function': '{func_name}'}})"
            )
        return results

    # ------------------------------------------------------------------
    # Code Generation — JavaScript
    # ------------------------------------------------------------------

    def generate_javascript(self, sheet_id: str) -> Optional[GeneratedCode]:
        """Generate JavaScript source code from an event sheet.

        Produces a self-contained ES module with an evaluateSheet() function
        that accepts game state and returns a list of action results.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None

        start_time = _time_module.time()
        lines: List[str] = []

        # Header
        lines.append("/**")
        lines.append(f" * Auto-generated event sheet: {sheet.name}")
        lines.append(f" * Generated by SparkLabs EngineEventCodegen")
        lines.append(f" * Sheet ID: {sheet.sheet_id}")
        lines.append(f" * Events: {len(sheet.events)}")
        lines.append(" */")
        lines.append("")
        lines.append("// ---- Comparison Helper ----")
        lines.append("")
        lines.append("function _compare(a, op, b) {")
        lines.append("    switch (op) {")
        lines.append("        case 'equal': return a === b;")
        lines.append("        case 'not_equal': return a !== b;")
        lines.append("        case 'greater': return parseFloat(a) > parseFloat(b);")
        lines.append("        case 'less': return parseFloat(a) < parseFloat(b);")
        lines.append("        case 'greater_equal': return parseFloat(a) >= parseFloat(b);")
        lines.append("        case 'less_equal': return parseFloat(a) <= parseFloat(b);")
        lines.append("        case 'between':")
        lines.append("            return Array.isArray(b) && b.length >= 2")
        lines.append("                ? b[0] <= a && a <= b[1] : false;")
        lines.append("        case 'contains':")
        lines.append("            return a != null && String(a).includes(String(b));")
        lines.append("        default: return false;")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # Event condition functions
        lines.append("// ---- Event Condition Functions ----")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            func_name = f"_checkEvent{idx}_{_sanitize_name_js(event.name)}"
            lines.append(f"function {func_name}(state) {{")
            lines.append(f"    // {event.name}")
            if not event.conditions:
                lines.append("    return true; // Always-fires event")
            else:
                for cond in event.conditions:
                    cond_line = self._emit_js_condition(cond)
                    lines.append(f"    {cond_line}")
                lines.append("    return true;")
            lines.append("}")
            lines.append("")

        # Event action functions
        lines.append("// ---- Event Action Functions ----")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            func_name = f"_executeEvent{idx}_{_sanitize_name_js(event.name)}"
            lines.append(f"function {func_name}(state) {{")
            lines.append(f"    // {event.name}")
            lines.append("    const results = [];")
            for action in event.actions:
                action_lines = self._emit_js_action(action)
                for al in action_lines:
                    lines.append(f"    {al}")
            lines.append("    return results;")
            lines.append("}")
            lines.append("")

        # Main evaluation
        lines.append("// ---- Main Evaluation Loop ----")
        lines.append("")
        lines.append("/**")
        lines.append(f" * Evaluate all events in sheet: {sheet.name}")
        lines.append(" * @param {Object} state - Game state dictionary")
        lines.append(" * @returns {Array} Action results")
        lines.append(" */")
        lines.append("function evaluateSheet(state) {")
        lines.append("    const allResults = [];")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            check_func = f"_checkEvent{idx}_{_sanitize_name_js(event.name)}"
            exec_func = f"_executeEvent{idx}_{_sanitize_name_js(event.name)}"
            lines.append(f"    // Event {idx}: {event.name}")
            if event.once_trigger:
                lines.append(
                    f"    if (!state['_event_{idx}_fired'] && {check_func}(state)) {{"
                )
                lines.append(f"        state['_event_{idx}_fired'] = true;")
                lines.append(f"        allResults.push(...{exec_func}(state));")
                lines.append("    }")
            else:
                lines.append(f"    if ({check_func}(state)) {{")
                lines.append(f"        allResults.push(...{exec_func}(state));")
                lines.append("    }")
        lines.append("    return allResults;")
        lines.append("}")
        lines.append("")
        lines.append("// ---- Exports ----")
        lines.append("export { evaluateSheet, _compare };")

        code_content = "\n".join(lines)
        self._generation_count += 1
        elapsed = _time_module.time() - start_time
        self._total_generation_time += elapsed

        generated = GeneratedCode(
            code_id=uuid.uuid4().hex,
            language=TargetLanguage.JAVASCRIPT,
            source_sheet_id=sheet_id,
            code_content=code_content,
            entry_point="evaluateSheet",
            dependencies=[],
            timestamp=_time_module.time(),
        )
        self._generated_code[generated.code_id] = generated
        return generated

    def _emit_js_condition(self, cond: EventCondition) -> str:
        """Emit JavaScript code for a single condition."""
        params = cond.parameters
        negate = "!" if cond.inverted else ""

        if cond.condition_type == ConditionType.ALWAYS:
            return "// Always-fires"
        elif cond.condition_type == ConditionType.COLLISION:
            obj_a = cond.target_object
            obj_b = params.get("with_object", "")
            return (
                f"if ({negate}(state.collisions || {{}})['{obj_a}'] === "
                f"'{obj_b}') return false;"
            )
        elif cond.condition_type == ConditionType.COMPARISON:
            obj = cond.target_object
            prop = params.get("property", "value")
            op = params.get("operator", "equal")
            val = params.get("value", 0)
            return (
                f"if ({negate}_compare(((state['{obj}'] || {{}})['{prop}'] || 0), "
                f"'{op}', {_js_repr(val)})) return false;"
            )
        elif cond.condition_type == ConditionType.TIMER:
            timer_name = params.get("timer_name", cond.target_object)
            threshold = params.get("threshold", 1.0)
            return (
                f"if ({negate}((state.timers || {{}})['{timer_name}'] || 0)"
                f" < {threshold}) return false;"
            )
        elif cond.condition_type == ConditionType.INPUT:
            key = params.get("key", "")
            pressed = params.get("pressed", True)
            if pressed:
                return (
                    f"if ({negate}(((state.input || {{}})['{key}'] || {{}})"
                    f".pressed)) return false;"
                )
            else:
                return (
                    f"if ({negate}!(((state.input || {{}})['{key}'] || {{}})"
                    f".pressed)) return false;"
                )
        elif cond.condition_type == ConditionType.VARIABLE:
            var_name = params.get("variable_name", "")
            op = params.get("operator", "equal")
            val = params.get("value", 0)
            return (
                f"if ({negate}_compare(((state.variables || {{}})['{var_name}'] || 0), "
                f"'{op}', {_js_repr(val)})) return false;"
            )
        elif cond.condition_type == ConditionType.OBJECT_COUNT:
            obj_type = params.get("object_type", cond.target_object)
            op = params.get("operator", "greater")
            count = params.get("count", 0)
            return (
                f"if ({negate}_compare("
                f"((state.objects || {{}})['{obj_type}'] || []).length, "
                f"'{op}', {count})) return false;"
            )
        elif cond.condition_type == ConditionType.SCENE_STATE:
            scene_name = params.get("scene_name", "")
            return (
                f"if ({negate}(state.current_scene || '') === "
                f"'{scene_name}') return false;"
            )
        elif cond.condition_type == ConditionType.RANDOM:
            probability = params.get("probability", 0.5)
            return (
                f"if ({negate}Math.random() < {probability}) return false;"
            )
        elif cond.condition_type == ConditionType.EXPRESSION:
            expr = params.get("expression", "true")
            return f"if ({negate}({expr})) return false;"
        elif cond.condition_type == ConditionType.DISTANCE:
            obj_a = cond.target_object
            obj_b = params.get("to_object", "")
            op = params.get("operator", "less")
            dist = params.get("distance", 100)
            return (
                f"if ({negate}_compare("
                f"Math.hypot("
                f"((state['{obj_a}'] || {{}}).x || 0) - "
                f"((state['{obj_b}'] || {{}}).x || 0), "
                f"((state['{obj_a}'] || {{}}).y || 0) - "
                f"((state['{obj_b}'] || {{}}).y || 0)),"
                f" '{op}', {dist})) return false;"
            )
        elif cond.condition_type == ConditionType.ANIMATION_STATE:
            obj = cond.target_object
            anim = params.get("animation_name", "")
            return (
                f"if ({negate}((state['{obj}'] || {{}}).animation || '') "
                f"=== '{anim}') return false;"
            )
        elif cond.condition_type == ConditionType.CUSTOM:
            func_name = params.get("function_name", "customCheck")
            return f"if ({negate}{func_name}(state)) return false;"
        return "// Unknown condition"

    def _emit_js_action(self, action: EventAction) -> List[str]:
        """Emit JavaScript code lines for a single action."""
        params = action.parameters
        results: List[str] = []

        if action.action_type == ActionType.MOVE:
            dx = params.get("x", 0)
            dy = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"const obj = state['{obj}'] = state['{obj}'] || {{}}; "
                f"obj.x = (obj.x || 0) + {dx}; obj.y = (obj.y || 0) + {dy};"
            )
            results.append(
                f"results.push({{action: 'move', target: '{obj}', "
                f"dx: {dx}, dy: {dy}}});"
            )
        elif action.action_type == ActionType.ROTATE:
            angle = params.get("angle", 0)
            obj = action.target_object
            results.append(
                f"const obj = state['{obj}'] = state['{obj}'] || {{}}; "
                f"obj.rotation = (obj.rotation || 0) + {angle};"
            )
            results.append(
                f"results.push({{action: 'rotate', target: '{obj}', "
                f"angle: {angle}}});"
            )
        elif action.action_type == ActionType.SCALE:
            sx = params.get("x", 1.0)
            sy = params.get("y", 1.0)
            obj = action.target_object
            results.append(
                f"const obj = state['{obj}'] = state['{obj}'] || {{}}; "
                f"obj.scaleX = (obj.scaleX || 1) * {sx}; "
                f"obj.scaleY = (obj.scaleY || 1) * {sy};"
            )
            results.append(
                f"results.push({{action: 'scale', target: '{obj}', "
                f"sx: {sx}, sy: {sy}}});"
            )
        elif action.action_type == ActionType.CREATE:
            obj_type = params.get("object_type", action.target_object)
            x = params.get("x", 0)
            y = params.get("y", 0)
            results.append(
                f"state.objects = state.objects || {{}}; "
                f"state.objects['{obj_type}'] = state.objects['{obj_type}'] || []; "
                f"state.objects['{obj_type}'].push({{x: {x}, y: {y}, type: '{obj_type}'}});"
            )
            results.append(
                f"results.push({{action: 'create', type: '{obj_type}', "
                f"x: {x}, y: {y}}});"
            )
        elif action.action_type == ActionType.DESTROY:
            obj = action.target_object
            results.append(f"delete state['{obj}'];")
            results.append(
                f"results.push({{action: 'destroy', target: '{obj}'}});"
            )
        elif action.action_type == ActionType.PLAY_SOUND:
            sound_id = params.get("sound_id", "")
            volume = params.get("volume", 1.0)
            results.append(
                f"results.push({{action: 'play_sound', sound_id: '{sound_id}', "
                f"volume: {volume}}});"
            )
        elif action.action_type == ActionType.CHANGE_SCENE:
            scene_name = params.get("scene_name", "")
            results.append(f"state.current_scene = '{scene_name}';")
            results.append(
                f"results.push({{action: 'change_scene', scene: '{scene_name}'}});"
            )
        elif action.action_type == ActionType.SET_VARIABLE:
            var_name = params.get("variable_name", "")
            value = params.get("value", 0)
            results.append(
                f"state.variables = state.variables || {{}}; "
                f"state.variables['{var_name}'] = {_js_repr(value)};"
            )
            results.append(
                f"results.push({{action: 'set_variable', name: '{var_name}', "
                f"value: {_js_repr(value)}}});"
            )
        elif action.action_type == ActionType.SPAWN:
            prefab = params.get("prefab_name", action.target_object)
            x = params.get("x", 0)
            y = params.get("y", 0)
            results.append(
                f"state.objects = state.objects || {{}}; "
                f"state.objects['{prefab}'] = state.objects['{prefab}'] || []; "
                f"state.objects['{prefab}'].push({{x: {x}, y: {y}, prefab: '{prefab}'}});"
            )
            results.append(
                f"results.push({{action: 'spawn', prefab: '{prefab}', "
                f"x: {x}, y: {y}}});"
            )
        elif action.action_type == ActionType.APPLY_FORCE:
            fx = params.get("x", 0)
            fy = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"const obj = state['{obj}'] = state['{obj}'] || {{}}; "
                f"obj.vx = (obj.vx || 0) + {fx}; obj.vy = (obj.vy || 0) + {fy};"
            )
            results.append(
                f"results.push({{action: 'apply_force', target: '{obj}', "
                f"fx: {fx}, fy: {fy}}});"
            )
        elif action.action_type == ActionType.PLAY_ANIMATION:
            anim_name = params.get("animation_name", "")
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] || {{}}; "
                f"state['{obj}'].animation = '{anim_name}';"
            )
            results.append(
                f"results.push({{action: 'play_animation', target: '{obj}', "
                f"animation: '{anim_name}'}});"
            )
        elif action.action_type == ActionType.TRIGGER_EVENT:
            event_name = params.get("event_name", "")
            results.append(
                f"results.push({{action: 'trigger_event', event: '{event_name}'}});"
            )
        elif action.action_type == ActionType.WAIT:
            duration = params.get("duration", 0.0)
            results.append(
                f"results.push({{action: 'wait', duration: {duration}}});"
            )
        elif action.action_type == ActionType.CALL_FUNCTION:
            func_name = params.get("function_name", "")
            func_args = params.get("arguments", [])
            results.append(
                f"results.push({{action: 'call_function', function: '{func_name}', "
                f"args: {_js_repr(func_args)}}});"
            )
        elif action.action_type == ActionType.SET_POSITION:
            x = params.get("x", 0)
            y = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"const obj = state['{obj}'] = state['{obj}'] || {{}}; "
                f"obj.x = {x}; obj.y = {y};"
            )
            results.append(
                f"results.push({{action: 'set_position', target: '{obj}', "
                f"x: {x}, y: {y}}});"
            )
        elif action.action_type == ActionType.TOGGLE:
            prop = params.get("property", "enabled")
            obj = action.target_object
            results.append(
                f"const obj = state['{obj}'] = state['{obj}'] || {{}}; "
                f"obj['{prop}'] = !(obj['{prop}'] || false);"
            )
            results.append(
                f"results.push({{action: 'toggle', target: '{obj}', "
                f"property: '{prop}'}});"
            )
        elif action.action_type == ActionType.CUSTOM:
            func_name = params.get("function_name", "customAction")
            results.append(
                f"results.push({{action: 'custom', function: '{func_name}'}});"
            )
        return results

    # ------------------------------------------------------------------
    # Code Generation — Lua
    # ------------------------------------------------------------------

    def generate_lua(self, sheet_id: str) -> Optional[GeneratedCode]:
        """Generate Lua source code from an event sheet.

        Produces a self-contained Lua module with an evaluate_sheet() function
        that accepts game state and returns a list of action results.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None

        start_time = _time_module.time()
        lines: List[str] = []

        # Header
        lines.append("--[[")
        lines.append(f" Auto-generated event sheet: {sheet.name}")
        lines.append(f" Generated by SparkLabs EngineEventCodegen")
        lines.append(f" Sheet ID: {sheet.sheet_id}")
        lines.append(f" Events: {len(sheet.events)}")
        lines.append("--]]")
        lines.append("")
        lines.append("-- ---- Comparison Helper ----")
        lines.append("")
        lines.append("local function _compare(a, op, b)")
        lines.append("    if op == 'equal' then return a == b end")
        lines.append("    if op == 'not_equal' then return a ~= b end")
        lines.append("    if op == 'greater' then return tonumber(a) > tonumber(b) end")
        lines.append("    if op == 'less' then return tonumber(a) < tonumber(b) end")
        lines.append("    if op == 'greater_equal' then return tonumber(a) >= tonumber(b) end")
        lines.append("    if op == 'less_equal' then return tonumber(a) <= tonumber(b) end")
        lines.append("    if op == 'between' then")
        lines.append("        if type(b) == 'table' and #b >= 2 then")
        lines.append("            return b[1] <= a and a <= b[2]")
        lines.append("        end")
        lines.append("        return false")
        lines.append("    end")
        lines.append("    if op == 'contains' then")
        lines.append("        return a ~= nil and string.find(tostring(a), tostring(b), 1, true) ~= nil")
        lines.append("    end")
        lines.append("    return false")
        lines.append("end")
        lines.append("")

        # Event condition functions
        lines.append("-- ---- Event Condition Functions ----")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            func_name = f"_check_event_{idx}_{_sanitize_name_lua(event.name)}"
            lines.append(f"local function {func_name}(state)")
            lines.append(f"    -- {event.name}")
            if not event.conditions:
                lines.append("    return true -- Always-fires event")
            else:
                for cond in event.conditions:
                    cond_line = self._emit_lua_condition(cond)
                    lines.append(f"    {cond_line}")
                lines.append("    return true")
            lines.append("end")
            lines.append("")

        # Event action functions
        lines.append("-- ---- Event Action Functions ----")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            func_name = f"_execute_event_{idx}_{_sanitize_name_lua(event.name)}"
            lines.append(f"local function {func_name}(state)")
            lines.append(f"    -- {event.name}")
            lines.append("    local results = {}")
            for action in event.actions:
                action_lines = self._emit_lua_action(action)
                for al in action_lines:
                    lines.append(f"    {al}")
            lines.append("    return results")
            lines.append("end")
            lines.append("")

        # Main evaluation
        lines.append("-- ---- Main Evaluation Loop ----")
        lines.append("")
        lines.append("--[[")
        lines.append(f" Evaluate all events in sheet: {sheet.name}")
        lines.append(" @param state table - Game state dictionary")
        lines.append(" @return table - Action results")
        lines.append("--]]")
        lines.append("local function evaluate_sheet(state)")
        lines.append("    local all_results = {}")
        for idx, event in enumerate(sheet.events):
            if not event.enabled:
                continue
            check_func = f"_check_event_{idx}_{_sanitize_name_lua(event.name)}"
            exec_func = f"_execute_event_{idx}_{_sanitize_name_lua(event.name)}"
            lines.append(f"    -- Event {idx}: {event.name}")
            if event.once_trigger:
                lines.append(
                    f"    if not state['_event_{idx}_fired'] and {check_func}(state) then"
                )
                lines.append(f"        state['_event_{idx}_fired'] = true")
                lines.append(f"        local res = {exec_func}(state)")
                lines.append("        for _, r in ipairs(res) do")
                lines.append("            table.insert(all_results, r)")
                lines.append("        end")
                lines.append("    end")
            else:
                lines.append(f"    if {check_func}(state) then")
                lines.append(f"        local res = {exec_func}(state)")
                lines.append("        for _, r in ipairs(res) do")
                lines.append("            table.insert(all_results, r)")
                lines.append("        end")
                lines.append("    end")
        lines.append("    return all_results")
        lines.append("end")
        lines.append("")
        lines.append("-- ---- Module Return ----")
        lines.append("return {")
        lines.append("    evaluate_sheet = evaluate_sheet,")
        lines.append("    _compare = _compare,")
        lines.append("}")

        code_content = "\n".join(lines)
        self._generation_count += 1
        elapsed = _time_module.time() - start_time
        self._total_generation_time += elapsed

        generated = GeneratedCode(
            code_id=uuid.uuid4().hex,
            language=TargetLanguage.LUA,
            source_sheet_id=sheet_id,
            code_content=code_content,
            entry_point="evaluate_sheet",
            dependencies=[],
            timestamp=_time_module.time(),
        )
        self._generated_code[generated.code_id] = generated
        return generated

    def _emit_lua_condition(self, cond: EventCondition) -> str:
        """Emit Lua code for a single condition."""
        params = cond.parameters
        negate = "not " if cond.inverted else ""

        if cond.condition_type == ConditionType.ALWAYS:
            return "-- Always-fires"
        elif cond.condition_type == ConditionType.COLLISION:
            obj_a = cond.target_object
            obj_b = params.get("with_object", "")
            return (
                f"if {negate}((state.collisions or {{}})['{obj_a}'] or '') == "
                f"'{obj_b}' then return false end"
            )
        elif cond.condition_type == ConditionType.COMPARISON:
            obj = cond.target_object
            prop = params.get("property", "value")
            op = params.get("operator", "equal")
            val = params.get("value", 0)
            return (
                f"if {negate}_compare(((state['{obj}'] or {{}})['{prop}'] or 0), "
                f"'{op}', {_lua_repr(val)}) then return false end"
            )
        elif cond.condition_type == ConditionType.TIMER:
            timer_name = params.get("timer_name", cond.target_object)
            threshold = params.get("threshold", 1.0)
            return (
                f"if {negate}((state.timers or {{}})['{timer_name}'] or 0) "
                f"< {threshold} then return false end"
            )
        elif cond.condition_type == ConditionType.INPUT:
            key = params.get("key", "")
            pressed = params.get("pressed", True)
            if pressed:
                return (
                    f"if {negate}(((state.input or {{}})['{key}'] or {{}})"
                    f".pressed) then return false end"
                )
            else:
                return (
                    f"if {negate}not (((state.input or {{}})['{key}'] or {{}})"
                    f".pressed) then return false end"
                )
        elif cond.condition_type == ConditionType.VARIABLE:
            var_name = params.get("variable_name", "")
            op = params.get("operator", "equal")
            val = params.get("value", 0)
            return (
                f"if {negate}_compare(((state.variables or {{}})['{var_name}'] or 0), "
                f"'{op}', {_lua_repr(val)}) then return false end"
            )
        elif cond.condition_type == ConditionType.OBJECT_COUNT:
            obj_type = params.get("object_type", cond.target_object)
            op = params.get("operator", "greater")
            count = params.get("count", 0)
            return (
                f"if {negate}_compare("
                f"#((state.objects or {{}})['{obj_type}'] or {{}}), "
                f"'{op}', {count}) then return false end"
            )
        elif cond.condition_type == ConditionType.SCENE_STATE:
            scene_name = params.get("scene_name", "")
            return (
                f"if {negate}(state.current_scene or '') == "
                f"'{scene_name}' then return false end"
            )
        elif cond.condition_type == ConditionType.RANDOM:
            probability = params.get("probability", 0.5)
            return (
                f"if {negate}math.random() < {probability} then return false end"
            )
        elif cond.condition_type == ConditionType.EXPRESSION:
            expr = params.get("expression", "true")
            return f"if {negate}({expr}) then return false end"
        elif cond.condition_type == ConditionType.DISTANCE:
            obj_a = cond.target_object
            obj_b = params.get("to_object", "")
            op = params.get("operator", "less")
            dist = params.get("distance", 100)
            return (
                f"if {negate}_compare("
                f"math.sqrt("
                f"(((state['{obj_a}'] or {{}}).x or 0) - "
                f"((state['{obj_b}'] or {{}}).x or 0))^2 + "
                f"(((state['{obj_a}'] or {{}}).y or 0) - "
                f"((state['{obj_b}'] or {{}}).y or 0))^2),"
                f" '{op}', {dist}) then return false end"
            )
        elif cond.condition_type == ConditionType.ANIMATION_STATE:
            obj = cond.target_object
            anim = params.get("animation_name", "")
            return (
                f"if {negate}((state['{obj}'] or {{}}).animation or '') "
                f"== '{anim}' then return false end"
            )
        elif cond.condition_type == ConditionType.CUSTOM:
            func_name = params.get("function_name", "custom_check")
            return f"if {negate}{func_name}(state) then return false end"
        return "-- Unknown condition"

    def _emit_lua_action(self, action: EventAction) -> List[str]:
        """Emit Lua code lines for a single action."""
        params = action.parameters
        results: List[str] = []

        if action.action_type == ActionType.MOVE:
            dx = params.get("x", 0)
            dy = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] or {{}}; "
                f"state['{obj}'].x = (state['{obj}'].x or 0) + {dx}; "
                f"state['{obj}'].y = (state['{obj}'].y or 0) + {dy}"
            )
            results.append(
                f"table.insert(results, {{action = 'move', target = '{obj}', "
                f"dx = {dx}, dy = {dy}}})"
            )
        elif action.action_type == ActionType.ROTATE:
            angle = params.get("angle", 0)
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] or {{}}; "
                f"state['{obj}'].rotation = (state['{obj}'].rotation or 0) + {angle}"
            )
            results.append(
                f"table.insert(results, {{action = 'rotate', target = '{obj}', "
                f"angle = {angle}}})"
            )
        elif action.action_type == ActionType.SCALE:
            sx = params.get("x", 1.0)
            sy = params.get("y", 1.0)
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] or {{}}; "
                f"state['{obj}'].scale_x = (state['{obj}'].scale_x or 1) * {sx}; "
                f"state['{obj}'].scale_y = (state['{obj}'].scale_y or 1) * {sy}"
            )
            results.append(
                f"table.insert(results, {{action = 'scale', target = '{obj}', "
                f"sx = {sx}, sy = {sy}}})"
            )
        elif action.action_type == ActionType.CREATE:
            obj_type = params.get("object_type", action.target_object)
            x = params.get("x", 0)
            y = params.get("y", 0)
            results.append(
                f"state.objects = state.objects or {{}}; "
                f"state.objects['{obj_type}'] = state.objects['{obj_type}'] or {{}}; "
                f"table.insert(state.objects['{obj_type}'], "
                f"{{x = {x}, y = {y}, type = '{obj_type}'}})"
            )
            results.append(
                f"table.insert(results, {{action = 'create', type = '{obj_type}', "
                f"x = {x}, y = {y}}})"
            )
        elif action.action_type == ActionType.DESTROY:
            obj = action.target_object
            results.append(f"state['{obj}'] = nil")
            results.append(
                f"table.insert(results, {{action = 'destroy', target = '{obj}'}})"
            )
        elif action.action_type == ActionType.PLAY_SOUND:
            sound_id = params.get("sound_id", "")
            volume = params.get("volume", 1.0)
            results.append(
                f"table.insert(results, {{action = 'play_sound', "
                f"sound_id = '{sound_id}', volume = {volume}}})"
            )
        elif action.action_type == ActionType.CHANGE_SCENE:
            scene_name = params.get("scene_name", "")
            results.append(f"state.current_scene = '{scene_name}'")
            results.append(
                f"table.insert(results, {{action = 'change_scene', "
                f"scene = '{scene_name}'}})"
            )
        elif action.action_type == ActionType.SET_VARIABLE:
            var_name = params.get("variable_name", "")
            value = params.get("value", 0)
            results.append(
                f"state.variables = state.variables or {{}}; "
                f"state.variables['{var_name}'] = {_lua_repr(value)}"
            )
            results.append(
                f"table.insert(results, {{action = 'set_variable', "
                f"name = '{var_name}', value = {_lua_repr(value)}}})"
            )
        elif action.action_type == ActionType.SPAWN:
            prefab = params.get("prefab_name", action.target_object)
            x = params.get("x", 0)
            y = params.get("y", 0)
            results.append(
                f"state.objects = state.objects or {{}}; "
                f"state.objects['{prefab}'] = state.objects['{prefab}'] or {{}}; "
                f"table.insert(state.objects['{prefab}'], "
                f"{{x = {x}, y = {y}, prefab = '{prefab}'}})"
            )
            results.append(
                f"table.insert(results, {{action = 'spawn', prefab = '{prefab}', "
                f"x = {x}, y = {y}}})"
            )
        elif action.action_type == ActionType.APPLY_FORCE:
            fx = params.get("x", 0)
            fy = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] or {{}}; "
                f"state['{obj}'].vx = (state['{obj}'].vx or 0) + {fx}; "
                f"state['{obj}'].vy = (state['{obj}'].vy or 0) + {fy}"
            )
            results.append(
                f"table.insert(results, {{action = 'apply_force', target = '{obj}', "
                f"fx = {fx}, fy = {fy}}})"
            )
        elif action.action_type == ActionType.PLAY_ANIMATION:
            anim_name = params.get("animation_name", "")
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] or {{}}; "
                f"state['{obj}'].animation = '{anim_name}'"
            )
            results.append(
                f"table.insert(results, {{action = 'play_animation', "
                f"target = '{obj}', animation = '{anim_name}'}})"
            )
        elif action.action_type == ActionType.TRIGGER_EVENT:
            event_name = params.get("event_name", "")
            results.append(
                f"table.insert(results, {{action = 'trigger_event', "
                f"event = '{event_name}'}})"
            )
        elif action.action_type == ActionType.WAIT:
            duration = params.get("duration", 0.0)
            results.append(
                f"table.insert(results, {{action = 'wait', duration = {duration}}})"
            )
        elif action.action_type == ActionType.CALL_FUNCTION:
            func_name = params.get("function_name", "")
            func_args = params.get("arguments", [])
            results.append(
                f"table.insert(results, {{action = 'call_function', "
                f"function = '{func_name}', args = {_lua_repr(func_args)}}})"
            )
        elif action.action_type == ActionType.SET_POSITION:
            x = params.get("x", 0)
            y = params.get("y", 0)
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] or {{}}; "
                f"state['{obj}'].x = {x}; state['{obj}'].y = {y}"
            )
            results.append(
                f"table.insert(results, {{action = 'set_position', "
                f"target = '{obj}', x = {x}, y = {y}}})"
            )
        elif action.action_type == ActionType.TOGGLE:
            prop = params.get("property", "enabled")
            obj = action.target_object
            results.append(
                f"state['{obj}'] = state['{obj}'] or {{}}; "
                f"state['{obj}']['{prop}'] = not (state['{obj}']['{prop}'] or false)"
            )
            results.append(
                f"table.insert(results, {{action = 'toggle', target = '{obj}', "
                f"property = '{prop}'}})"
            )
        elif action.action_type == ActionType.CUSTOM:
            func_name = params.get("function_name", "custom_action")
            results.append(
                f"table.insert(results, {{action = 'custom', "
                f"function = '{func_name}'}})"
            )
        return results

    # ------------------------------------------------------------------
    # Template System
    # ------------------------------------------------------------------

    def get_template(self, template_type: str) -> Optional[CodeTemplate]:
        """Retrieve a pre-built event template by its type name.

        Available template types:
          - PLATFORMER_MOVEMENT: Horizontal input + jump + gravity
          - COLLISION_RESPONSE: Overlap detection + bounce/collect
          - TIMER_SPAWNING: Interval-based object creation
          - UI_BUTTON_HANDLING: Hover/click/press state transitions

        Args:
            template_type: Template type identifier (e.g., 'PLATFORMER_MOVEMENT').

        Returns:
            CodeTemplate with parameter slots ready for substitution.
        """
        return self._templates.get(template_type)

    def apply_template(
        self,
        sheet_id: str,
        template_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[GeneratedCode]:
        """Apply a pre-built template to an event sheet by filling its slots.

        Substitutes the template's parameter slots with the provided values
        and emits generated code for the target language.

        Args:
            sheet_id: ID of the event sheet to apply the template to.
            template_type: Template type identifier.
            parameters: Values to substitute into the template slots.

        Returns:
            GeneratedCode with the instantiated template.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        template = self._templates.get(template_type)
        if template is None:
            return None

        params = parameters or {}
        filled_code = template.template_code
        for slot_name, default_value in template.parameter_slots.items():
            value = params.get(slot_name, default_value)
            filled_code = filled_code.replace(f"{{{slot_name}}}", str(value))

        generated = GeneratedCode(
            code_id=uuid.uuid4().hex,
            language=template.language,
            source_sheet_id=sheet_id,
            code_content=filled_code,
            entry_point=f"{template.name.lower().replace(' ', '_')}_generated",
            dependencies=[],
            timestamp=_time_module.time(),
        )
        self._generated_code[generated.code_id] = generated
        return generated

    # ------------------------------------------------------------------
    # Status & Reset
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a snapshot of the codegen system's current state.

        Includes sheet counts, generation statistics, and timing metrics.
        """
        avg_time = (
            self._total_generation_time / max(self._generation_count, 1)
        )
        return {
            "total_sheets": len(self._sheets),
            "total_events": sum(len(s.events) for s in self._sheets.values()),
            "total_generated": self._generation_count,
            "total_templates": len(self._templates),
            "avg_generation_time_ms": round(avg_time * 1000, 2),
            "total_generation_time_s": round(self._total_generation_time, 3),
            "max_sheets": self.MAX_SHEETS,
            "max_events_per_sheet": self.MAX_EVENTS_PER_SHEET,
            "max_conditions_per_event": self.MAX_CONDITIONS_PER_EVENT,
            "max_actions_per_event": self.MAX_ACTIONS_PER_EVENT,
        }

    def reset(self) -> None:
        """Reset all data in the codegen system.

        Clears all event sheets, generated code, and templates, then
        re-initializes built-in templates.
        """
        self._sheets.clear()
        self._generated_code.clear()
        self._templates.clear()
        self._generation_count = 0
        self._total_generation_time = 0.0
        self._init_templates()


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _sanitize_name(name: str) -> str:
    """Sanitize an event name into a valid Python identifier."""
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    if not sanitized:
        sanitized = "event"
    if sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized.lower()


def _sanitize_name_js(name: str) -> str:
    """Sanitize an event name into a valid JavaScript identifier."""
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    if not sanitized:
        sanitized = "event"
    if sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized


def _sanitize_name_lua(name: str) -> str:
    """Sanitize an event name into a valid Lua identifier."""
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    if not sanitized:
        sanitized = "event"
    if sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized.lower()


def _js_repr(value: Any) -> str:
    """Convert a Python value to a JavaScript literal string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        return f"'{value}'"
    elif isinstance(value, (list, tuple)):
        items = ", ".join(_js_repr(v) for v in value)
        return f"[{items}]"
    elif isinstance(value, dict):
        pairs = ", ".join(f"{_js_repr(k)}: {_js_repr(v)}" for k, v in value.items())
        return f"{{{pairs}}}"
    elif value is None:
        return "null"
    return str(value)


def _lua_repr(value: Any) -> str:
    """Convert a Python value to a Lua literal string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        return f"'{value}'"
    elif isinstance(value, (list, tuple)):
        items = ", ".join(_lua_repr(v) for v in value)
        return f"{{{items}}}"
    elif isinstance(value, dict):
        pairs = ", ".join(
            f"[{_lua_repr(k)}] = {_lua_repr(v)}" for k, v in value.items()
        )
        return f"{{{pairs}}}"
    elif value is None:
        return "nil"
    return str(value)


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_engine_event_codegen() -> EngineEventCodegen:
    """Return the singleton EngineEventCodegen instance."""
    return EngineEventCodegen.get_instance()