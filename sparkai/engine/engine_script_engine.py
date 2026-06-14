"""
Engine Script Engine - Script-to-engine binding layer for AI-generated game logic.
Provides runtime script execution, event binding, expression evaluation,
and safe sandboxed scripting for the SparkLabs AI-native game engine.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable


class ScriptLanguage(Enum):
    """Supported scripting languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    LUA = "lua"
    VISUAL_SCRIPT = "visual_script"


class ScriptEvent(Enum):
    """Standard script events."""
    ON_START = "on_start"
    ON_UPDATE = "on_update"
    ON_FIXED_UPDATE = "on_fixed_update"
    ON_COLLISION = "on_collision"
    ON_TRIGGER = "on_trigger"
    ON_DESTROY = "on_destroy"
    ON_INPUT = "on_input"
    ON_TIMER = "on_timer"
    ON_ANIMATION_END = "on_animation_end"
    ON_CUSTOM = "on_custom"


@dataclass
class ScriptBinding:
    """A binding between a script and a game entity."""
    binding_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    script_source: str = ""
    language: ScriptLanguage = ScriptLanguage.PYTHON
    compiled_script: Optional[Any] = None
    event_handlers: Dict[str, Callable] = field(default_factory=dict)
    is_active: bool = True
    execution_count: int = 0
    last_execution: float = 0.0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "entity_id": self.entity_id,
            "language": self.language.value,
            "is_active": self.is_active,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
        }


@dataclass
class ScriptContext:
    """Execution context for a script."""
    context_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    engine_api: Dict[str, Any] = field(default_factory=dict)
    is_sandboxed: bool = True
    max_execution_time: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "entity_id": self.entity_id,
            "variables": self.variables,
            "is_sandboxed": self.is_sandboxed,
        }


@dataclass
class ScriptExpression:
    """A compiled expression for evaluation."""
    expression_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source: str = ""
    compiled: Optional[Any] = None
    language: ScriptLanguage = ScriptLanguage.PYTHON
    parse_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expression_id": self.expression_id,
            "source": self.source,
            "language": self.language.value,
        }


class EngineScriptEngine:
    """
    Script-to-engine binding layer for AI-generated game logic.
    Provides runtime script execution, event binding, expression
    evaluation, and safe sandboxed scripting.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._bindings: Dict[str, ScriptBinding] = {}
            self._contexts: Dict[str, ScriptContext] = {}
            self._expressions: Dict[str, ScriptExpression] = {}
            self._event_listeners: Dict[str, Dict[str, List[str]]] = {}
            self._global_variables: Dict[str, Any] = {}
            self._engine_api_registry: Dict[str, Callable] = {}
            self._execution_history: List[Dict[str, Any]] = []
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'EngineScriptEngine':
        return cls()

    def register_engine_api(self, name: str, func: Callable):
        """Register an engine API function callable from scripts."""
        self._engine_api_registry[name] = func

    def create_binding(self, entity_id: str, script_source: str,
                       language: ScriptLanguage = ScriptLanguage.PYTHON) -> ScriptBinding:
        """Create a script binding for an entity."""
        binding = ScriptBinding(
            entity_id=entity_id,
            script_source=script_source,
            language=language,
        )
        self._bindings[binding.binding_id] = binding
        return binding

    def bind_event(self, binding_id: str, event: ScriptEvent,
                   handler: Callable):
        """Bind a handler function to a script event."""
        binding = self._bindings.get(binding_id)
        if binding:
            binding.event_handlers[event.value] = handler

    def create_context(self, entity_id: str, variables: Dict[str, Any] = None) -> ScriptContext:
        """Create a script execution context."""
        context = ScriptContext(
            entity_id=entity_id,
            variables=variables or {},
            engine_api=dict(self._engine_api_registry),
        )
        self._contexts[context.context_id] = context
        return context

    def set_variable(self, context_id: str, name: str, value: Any):
        """Set a variable in a script context."""
        context = self._contexts.get(context_id)
        if context:
            context.variables[name] = value

    def get_variable(self, context_id: str, name: str) -> Optional[Any]:
        """Get a variable from a script context."""
        context = self._contexts.get(context_id)
        return context.variables.get(name) if context else None

    def set_global(self, name: str, value: Any):
        """Set a global variable accessible to all scripts."""
        self._global_variables[name] = value

    def get_global(self, name: str) -> Optional[Any]:
        """Get a global variable."""
        return self._global_variables.get(name)

    def compile_expression(self, source: str,
                           language: ScriptLanguage = ScriptLanguage.PYTHON) -> ScriptExpression:
        """Compile an expression for later evaluation."""
        expression = ScriptExpression(source=source, language=language)

        parse_start = _time_module.time()
        if language == ScriptLanguage.PYTHON:
            try:
                expression.compiled = compile(source, "<script>", "eval")
            except SyntaxError:
                expression.compiled = None
        expression.parse_time = _time_module.time() - parse_start

        self._expressions[expression.expression_id] = expression
        return expression

    def evaluate(self, expression_id: str, context: Dict[str, Any] = None) -> Any:
        """Evaluate a compiled expression."""
        expression = self._expressions.get(expression_id)
        if not expression or not expression.compiled:
            return None

        try:
            if expression.language == ScriptLanguage.PYTHON:
                eval_context = dict(self._global_variables)
                if context:
                    eval_context.update(context)
                return eval(expression.compiled, {"__builtins__": {}}, eval_context)
        except Exception as e:
            self._execution_history.append({
                "expression_id": expression_id,
                "error": str(e),
                "timestamp": _time_module.time(),
            })
            return None

    def execute_binding(self, binding_id: str, event: ScriptEvent,
                        context: Optional[ScriptContext] = None):
        """Execute a script binding for a specific event."""
        binding = self._bindings.get(binding_id)
        if not binding or not binding.is_active:
            return

        handler = binding.event_handlers.get(event.value)
        if not handler:
            return

        try:
            handler(context)
            binding.execution_count += 1
            binding.last_execution = _time_module.time()
        except Exception as e:
            binding.error_count += 1
            self._execution_history.append({
                "binding_id": binding_id,
                "event": event.value,
                "error": str(e),
                "timestamp": _time_module.time(),
            })

    def execute_entity_event(self, entity_id: str, event: ScriptEvent,
                             context: Optional[ScriptContext] = None):
        """Execute all bindings for an entity on a specific event."""
        for binding in self._bindings.values():
            if binding.entity_id == entity_id and binding.is_active:
                self.execute_binding(binding.binding_id, event, context)

    def execute_python(self, source: str, context: Dict[str, Any] = None) -> Any:
        """Execute arbitrary Python code in a sandboxed environment."""
        exec_context = dict(self._global_variables)
        if context:
            exec_context.update(context)

        safe_builtins = {
            "abs": abs, "all": all, "any": any, "bool": bool,
            "dict": dict, "enumerate": enumerate, "filter": filter,
            "float": float, "int": int, "len": len, "list": list,
            "map": map, "max": max, "min": min, "range": range,
            "round": round, "set": set, "sorted": sorted, "str": str,
            "sum": sum, "tuple": tuple, "zip": zip, "print": print,
        }

        try:
            return eval(source, {"__builtins__": safe_builtins}, exec_context)
        except Exception as e:
            self._execution_history.append({
                "source": source[:100],
                "error": str(e),
                "timestamp": _time_module.time(),
            })
            return None

    def listen_event(self, entity_id: str, event: ScriptEvent, binding_id: str):
        """Register a listener for an event on an entity."""
        self._event_listeners.setdefault(entity_id, {}).setdefault(event.value, []).append(binding_id)

    def dispatch_event(self, entity_id: str, event: ScriptEvent,
                       event_data: Dict[str, Any] = None):
        """Dispatch an event to all registered listeners."""
        listeners = self._event_listeners.get(entity_id, {}).get(event.value, [])
        for binding_id in listeners:
            context = self.create_context(entity_id, event_data)
            self.execute_binding(binding_id, event, context)

    def get_binding(self, binding_id: str) -> Optional[ScriptBinding]:
        """Get a script binding by ID."""
        return self._bindings.get(binding_id)

    def list_bindings(self, entity_id: str = "") -> List[ScriptBinding]:
        """List all bindings, optionally filtered by entity."""
        if entity_id:
            return [b for b in self._bindings.values() if b.entity_id == entity_id]
        return list(self._bindings.values())

    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return self._execution_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get script engine statistics."""
        return {
            "total_bindings": len(self._bindings),
            "active_bindings": sum(1 for b in self._bindings.values() if b.is_active),
            "total_contexts": len(self._contexts),
            "total_expressions": len(self._expressions),
            "total_api_registered": len(self._engine_api_registry),
            "total_globals": len(self._global_variables),
            "total_executions": sum(b.execution_count for b in self._bindings.values()),
            "total_errors": sum(b.error_count for b in self._bindings.values()),
            "recent_history": len(self._execution_history),
        }


def get_script_engine() -> EngineScriptEngine:
    return EngineScriptEngine.get_instance()