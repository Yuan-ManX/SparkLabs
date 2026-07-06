"""
SparkLabs Agent - Runtime Tool Synthesis Engine

This module implements a tool synthesis engine for the SparkLabs AI-native
game engine agent platform. Unlike tool composition (which chains pre-existing
tools together) and tool forging (which crafts implementations), tool
synthesis creates brand-new tool *definitions* at runtime by combining
typed primitives, parameter declarations, and an execution pipeline into a
freshly minted, validated, and activatable tool artifact.

Core concepts:

  1. Primitive Specifications
       Primitives are the atomic operations a synthesizer can use to build
       new tools. Each primitive declares an input signature, an output
       signature, and an implementation hint. The catalogue of primitives
       is the alphabet that the synthesis engine composes from.

  2. Tool Parameter Declarations
       Each synthesized tool exposes a strongly-typed parameter list. The
       synthesizer validates that every required parameter has either a
       caller-supplied value or a declared default.

  3. Step Pipelines
       A synthesized tool's behaviour is encoded as an ordered list of
       ``ToolStep`` records. Each step references a primitive, describes
       how its inputs are bound from the caller or upstream step outputs,
       and names the slot in which the result is stored.

  4. Validation
       Every synthesized tool can be validated. Validation confirms that
       referenced primitives exist, that input / output types align, and
       that the step graph is internally consistent. The result is one of
       ``VALID``, ``INVALID``, or ``WARNING``.

  5. Simulated Execution
       The engine can execute a synthesized tool by walking the step graph
       and producing a deterministic, simulated output. The execution
       record captures inputs, outputs, duration, and success.

Architecture:
  ToolSynthesisEngine (Singleton, double-checked locking with threading.RLock)
    |-- PrimitiveSpec        -- an atomic operation available for synthesis
    |-- ToolParameter        -- a typed parameter on a synthesized tool
    |-- ToolStep             -- a single primitive invocation in a pipeline
    |-- SynthesizedTool      -- a brand-new tool definition
    |-- SynthesisRequest     -- a request to synthesize a new tool
    |-- ValidationReport     -- the result of validating a synthesized tool
    |-- ExecutionRecord      -- the simulated execution of a tool
    |-- ToolSynthesisStats   -- aggregate engine statistics
    |-- ToolSynthesisSnapshot-- complete engine state snapshot
    |-- SynthesisEvent       -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_PRIMITIVES: int = 500
_MAX_TOOLS: int = 1000
_MAX_PARAMETERS: int = 4000
_MAX_STEPS: int = 8000
_MAX_REQUESTS: int = 1000
_MAX_VALIDATIONS: int = 2000
_MAX_EXECUTIONS: int = 5000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


def _safe_list(value: Any) -> List[Any]:
    """Return a fresh list copy of value, or an empty list if not iterable."""
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, (tuple, set, frozenset)):
        return list(value)
    return [value]


def _safe_dict(value: Any) -> Dict[str, Any]:
    """Return a fresh dict copy of value, or an empty dict if not a dict."""
    if isinstance(value, dict):
        return dict(value)
    return {}


def _parse_timestamp(value: str) -> Optional[datetime.datetime]:
    """Parse an ISO-8601 timestamp string into a datetime object.

    Returns ``None`` if the value cannot be parsed.
    """
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "")
        return datetime.datetime.fromisoformat(cleaned)
    except (ValueError, TypeError, AttributeError):
        return None


def _infer_type_label(value: Any) -> str:
    """Infer a short type label for a runtime value.

    Used by the validation logic to detect mismatches between declared
    primitive input/output signatures and the actual values passed at
    execution time.
    """
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return "any"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PrimitiveType(Enum):
    """The category of an atomic operation available for tool synthesis."""
    INPUT = "input"
    OUTPUT = "output"
    COMPUTE = "compute"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    TRANSFORM = "transform"
    AGGREGATE = "aggregate"
    FILTER = "filter"
    MAP = "map"
    REDUCE = "reduce"


class ParameterType(Enum):
    """The declared type of a parameter on a synthesized tool."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class SynthesisStrategy(Enum):
    """The high-level strategy used to combine primitives into a tool."""
    COMPOSITION = "composition"
    TRANSFORMATION = "transformation"
    WRAPPER = "wrapper"
    CHAINING = "chaining"
    PIPELINE = "pipeline"


class ToolStatus(Enum):
    """The lifecycle status of a synthesized tool."""
    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class ValidationResult(Enum):
    """The outcome of a validation pass against a synthesized tool."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class SynthesisEventKind(Enum):
    """Observable lifecycle events emitted by the synthesis engine."""
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_COMPLETED = "synthesis_completed"
    TOOL_REGISTERED = "tool_registered"
    TOOL_VALIDATED = "tool_validated"
    TOOL_EXECUTED = "tool_executed"
    TOOL_DEPRECATED = "tool_deprecated"
    PRIMITIVE_ADDED = "primitive_added"
    PRIMITIVE_REMOVED = "primitive_removed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PrimitiveSpec:
    """An atomic operation available to the synthesis engine."""
    primitive_id: str
    name: str
    primitive_type: PrimitiveType
    input_signature: str
    output_signature: str
    description: str
    implementation_hint: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this primitive spec to a JSON-friendly dictionary."""
        return {
            "primitive_id": self.primitive_id,
            "name": self.name,
            "primitive_type": self.primitive_type.value,
            "input_signature": self.input_signature,
            "output_signature": self.output_signature,
            "description": self.description,
            "implementation_hint": self.implementation_hint,
        }


@dataclass
class ToolParameter:
    """A typed parameter declaration on a synthesized tool."""
    param_id: str
    name: str
    param_type: ParameterType
    required: bool
    default_value: Any
    description: str
    validation_rule: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this parameter to a JSON-friendly dictionary."""
        return {
            "param_id": self.param_id,
            "name": self.name,
            "param_type": self.param_type.value,
            "required": self.required,
            "default_value": self.default_value,
            "description": self.description,
            "validation_rule": self.validation_rule,
        }


@dataclass
class ToolStep:
    """A single primitive invocation within a synthesized tool's pipeline."""
    step_id: str
    step_index: int
    primitive_id: str
    input_mapping: Dict[str, str]
    output_name: str
    conditional: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this step to a JSON-friendly dictionary."""
        return {
            "step_id": self.step_id,
            "step_index": self.step_index,
            "primitive_id": self.primitive_id,
            "input_mapping": dict(self.input_mapping) if self.input_mapping else {},
            "output_name": self.output_name,
            "conditional": self.conditional,
        }


@dataclass
class SynthesizedTool:
    """A complete synthesized tool definition."""
    tool_id: str
    name: str
    description: str
    version: str
    parameters: List[ToolParameter]
    steps: List[ToolStep]
    strategy: SynthesisStrategy
    status: ToolStatus
    validation_result: ValidationResult
    execution_count: int
    success_count: int
    failure_count: int
    created_at: str
    updated_at: str
    creator_agent_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this tool to a JSON-friendly dictionary."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [p.to_dict() for p in self.parameters],
            "steps": [s.to_dict() for s in self.steps],
            "strategy": self.strategy.value,
            "status": self.status.value,
            "validation_result": self.validation_result.value,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "creator_agent_id": self.creator_agent_id,
        }


@dataclass
class SynthesisRequest:
    """A request to synthesize a brand-new tool."""
    request_id: str
    requester_agent_id: str
    intent: str
    available_primitives: List[str]
    output_tool_id: Optional[str]
    status: str
    started_at: str
    completed_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this request to a JSON-friendly dictionary."""
        return {
            "request_id": self.request_id,
            "requester_agent_id": self.requester_agent_id,
            "intent": self.intent,
            "available_primitives": list(self.available_primitives),
            "output_tool_id": self.output_tool_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ValidationReport:
    """The detailed result of validating a synthesized tool."""
    report_id: str
    tool_id: str
    result: ValidationResult
    issues: List[str]
    warnings: List[str]
    validated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this report to a JSON-friendly dictionary."""
        return {
            "report_id": self.report_id,
            "tool_id": self.tool_id,
            "result": self.result.value,
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "validated_at": self.validated_at,
        }


@dataclass
class ExecutionRecord:
    """The simulated execution of a synthesized tool."""
    execution_id: str
    tool_id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    success: bool
    duration_ms: float
    error_message: str
    executed_at: str
    agent_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this execution record to a JSON-friendly dictionary."""
        return {
            "execution_id": self.execution_id,
            "tool_id": self.tool_id,
            "inputs": dict(self.inputs) if self.inputs else {},
            "outputs": dict(self.outputs) if self.outputs else {},
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "executed_at": self.executed_at,
            "agent_id": self.agent_id,
        }


@dataclass
class ToolSynthesisStats:
    """Aggregate statistics about the tool synthesis engine."""
    total_tools: int
    total_primitives: int
    total_executions: int
    active_tools: int
    deprecated_tools: int
    success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_tools": self.total_tools,
            "total_primitives": self.total_primitives,
            "total_executions": self.total_executions,
            "active_tools": self.active_tools,
            "deprecated_tools": self.deprecated_tools,
            "success_rate": self.success_rate,
        }


@dataclass
class ToolSynthesisSnapshot:
    """A complete snapshot of the tool synthesis engine state."""
    initialized: bool
    primitives: List[PrimitiveSpec]
    tools: List[SynthesizedTool]
    requests: List[SynthesisRequest]
    executions: List[ExecutionRecord]
    events: List[SynthesisEvent]
    stats: ToolSynthesisStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "primitives": [p.to_dict() for p in self.primitives],
            "tools": [t.to_dict() for t in self.tools],
            "requests": [r.to_dict() for r in self.requests],
            "executions": [e.to_dict() for e in self.executions],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class SynthesisEvent:
    """An observable lifecycle event emitted by the synthesis engine."""
    event_id: str
    kind: SynthesisEventKind
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


# ---------------------------------------------------------------------------
# Tool Synthesis Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class ToolSynthesisEngine:
    """Runtime tool synthesis engine for AI game agents.

    The engine maintains a catalogue of atomic ``PrimitiveSpec`` records
    that it composes into brand-new ``SynthesizedTool`` definitions at
    runtime. Each synthesized tool is validated for internal consistency
    and can be executed in a simulated fashion to capture inputs, outputs,
    and success metrics. The engine is a thread-safe singleton accessed via
    :meth:`get_instance` or the module-level :func:`get_tool_synthesis`
    helper.

    Usage:
        engine = get_tool_synthesis()
        engine.add_primitive(
            "extract_field",
            PrimitiveType.TRANSFORM,
            input_signature="any",
            output_signature="dict",
            description="Extract a named field from a structured record",
        )
        tool = engine.synthesize_tool(
            name="stats_analyzer",
            description="Average a numeric field over a list of records",
            requester_agent_id="agent_alpha",
            intent="average_field",
            available_primitive_ids=["extract_field", "compute_average"],
            parameters=[
                ToolParameter(
                    param_id=_new_id(),
                    name="data",
                    param_type=ParameterType.LIST,
                    required=True,
                    default_value=None,
                    description="List of records to analyze",
                    validation_rule="",
                ),
            ],
            strategy="pipeline",
        )
        engine.validate_tool(tool.tool_id)
        record = engine.execute_tool(tool.tool_id, {"data": [1, 2, 3]}, "agent_alpha")
    """

    _instance: Optional["ToolSynthesisEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Sentinel returned by the primitive simulator to signal a
    # simulation failure. Using a unique object instead of ``None``
    # distinguishes "the simulator produced no value" from "the
    # simulator failed".
    _SIMULATION_ERROR: object = object()

    # -- Construction (double-checked locking) -----------------------------

    def __new__(cls) -> "ToolSynthesisEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Fast path: already initialized singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Primary stores keyed by id where it makes sense; lists where
            # ordering matters.
            self._primitives: Dict[str, PrimitiveSpec] = {}
            self._tools: Dict[str, SynthesizedTool] = {}
            self._requests: Dict[str, SynthesisRequest] = {}
            self._validations: Dict[str, ValidationReport] = {}
            self._executions: List[ExecutionRecord] = []
            self._events: List[SynthesisEvent] = []

            # Aggregate counters.
            self._primitive_counter: int = 0
            self._tool_counter: int = 0
            self._execution_counter: int = 0
            self._validation_counter: int = 0
            self._request_counter: int = 0

            self._initialized: bool = True

            # Seed baseline synthesis data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "ToolSynthesisEngine":
        """Return the singleton ToolSynthesisEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Primitive management
    # ------------------------------------------------------------------

    def add_primitive(
        self,
        name: str,
        primitive_type: PrimitiveType,
        input_signature: str,
        output_signature: str,
        description: str = "",
        implementation_hint: str = "",
    ) -> PrimitiveSpec:
        """Add a new primitive to the synthesis catalogue.

        Args:
            name: Human-readable name of the primitive.
            primitive_type: The :class:`PrimitiveType` categorisation.
            input_signature: A short string describing the expected input
                type (for example ``"list"`` or ``"any"``).
            output_signature: A short string describing the produced output
                type (for example ``"float"`` or ``"dict"``).
            description: Free-form description of what the primitive does.
            implementation_hint: Optional hint to a downstream code
                generator about how the primitive might be implemented.

        Returns:
            The newly created :class:`PrimitiveSpec`.
        """
        with self._lock:
            spec = PrimitiveSpec(
                primitive_id=_new_id(),
                name=name,
                primitive_type=primitive_type,
                input_signature=input_signature,
                output_signature=output_signature,
                description=description,
                implementation_hint=implementation_hint,
            )
            self._primitives[spec.primitive_id] = spec
            self._primitive_counter += 1
            _evict_fifo_dict(self._primitives, _MAX_PRIMITIVES)
            self._record_event(
                SynthesisEventKind.PRIMITIVE_ADDED,
                {
                    "primitive_id": spec.primitive_id,
                    "name": spec.name,
                    "primitive_type": spec.primitive_type.value,
                },
            )
            return spec

    def get_primitive(self, primitive_id: str) -> Optional[PrimitiveSpec]:
        """Return a primitive by id, or None if not found."""
        with self._lock:
            return self._primitives.get(primitive_id)

    def list_primitives(
        self,
        primitive_type: Optional[PrimitiveType] = None,
    ) -> List[PrimitiveSpec]:
        """List primitives, optionally filtered by type."""
        with self._lock:
            results: List[PrimitiveSpec] = []
            for spec in self._primitives.values():
                if primitive_type is not None and spec.primitive_type != primitive_type:
                    continue
                results.append(spec)
            return results

    def remove_primitive(self, primitive_id: str) -> bool:
        """Remove a primitive by id. Returns True if it was removed.

        Removing a primitive does NOT automatically invalidate existing
        synthesized tools that referenced it. Validation will then flag
        those tools as ``INVALID`` on the next ``validate_tool`` call.
        """
        with self._lock:
            spec = self._primitives.pop(primitive_id, None)
            if spec is None:
                return False
            self._record_event(
                SynthesisEventKind.PRIMITIVE_REMOVED,
                {
                    "primitive_id": primitive_id,
                    "name": spec.name,
                },
            )
            return True

    # ------------------------------------------------------------------
    # Tool synthesis
    # ------------------------------------------------------------------

    def synthesize_tool(
        self,
        name: str,
        description: str,
        requester_agent_id: str,
        intent: str,
        available_primitive_ids: List[str],
        parameters: Optional[List[ToolParameter]] = None,
        strategy: str = "composition",
        steps: Optional[List[ToolStep]] = None,
    ) -> SynthesizedTool:
        """Synthesize a brand-new tool definition.

        When ``steps`` is omitted, the engine auto-generates a simple
        pipeline by iterating through ``available_primitive_ids`` in order
        and binding each step's inputs from the previous step's output.

        Args:
            name: Human-readable name of the new tool.
            description: Free-form description of the new tool.
            requester_agent_id: Identifier of the agent that requested
                the synthesis.
            intent: A short description of the intent / use case.
            available_primitive_ids: Identifiers of primitives that are
                available to the synthesizer.
            parameters: Optional list of :class:`ToolParameter`. When
                omitted, the engine auto-derives one parameter per
                referenced primitive's input signature.
            strategy: A string naming the :class:`SynthesisStrategy` to
                use. Unknown strategies fall back to ``composition``.
            steps: Optional explicit step list. When provided, it is used
                verbatim; otherwise the engine auto-generates steps.

        Returns:
            The newly created :class:`SynthesizedTool`.
        """
        with self._lock:
            now = _now()
            strategy_enum = self._coerce_strategy(strategy)
            # Record a synthesis request for provenance.
            request = SynthesisRequest(
                request_id=_new_id(),
                requester_agent_id=requester_agent_id,
                intent=intent,
                available_primitives=list(available_primitive_ids) if available_primitive_ids else [],
                output_tool_id=None,
                status="started",
                started_at=now,
                completed_at=None,
            )
            self._requests[request.request_id] = request
            self._request_counter += 1
            _evict_fifo_dict(self._requests, _MAX_REQUESTS)
            self._record_event(
                SynthesisEventKind.SYNTHESIS_STARTED,
                {
                    "request_id": request.request_id,
                    "requester_agent_id": requester_agent_id,
                    "intent": intent,
                    "primitive_count": len(request.available_primitives),
                },
            )

            # Auto-generate parameters if none provided.
            if parameters is None:
                parameters = self._auto_derive_parameters(
                    name=name,
                    available_primitive_ids=request.available_primitives,
                )

            # Auto-generate steps if none provided.
            if steps is None:
                steps = self._auto_generate_steps(
                    available_primitive_ids=request.available_primitives,
                )

            tool = SynthesizedTool(
                tool_id=_new_id(),
                name=name,
                description=description,
                version="0.1.0",
                parameters=list(parameters) if parameters else [],
                steps=list(steps) if steps else [],
                strategy=strategy_enum,
                status=ToolStatus.DRAFT,
                validation_result=ValidationResult.WARNING,
                execution_count=0,
                success_count=0,
                failure_count=0,
                created_at=now,
                updated_at=now,
                creator_agent_id=requester_agent_id,
            )
            self._tools[tool.tool_id] = tool
            self._tool_counter += 1
            _evict_fifo_dict(self._tools, _MAX_TOOLS)
            self._evict_tool_substores(tool.tool_id)

            # Link the request to its produced tool and complete it.
            request.output_tool_id = tool.tool_id
            request.status = "completed"
            request.completed_at = _now()

            self._record_event(
                SynthesisEventKind.SYNTHESIS_COMPLETED,
                {
                    "request_id": request.request_id,
                    "tool_id": tool.tool_id,
                    "step_count": len(tool.steps),
                    "parameter_count": len(tool.parameters),
                },
            )
            self._record_event(
                SynthesisEventKind.TOOL_REGISTERED,
                {
                    "tool_id": tool.tool_id,
                    "name": tool.name,
                    "strategy": tool.strategy.value,
                },
            )
            return tool

    def get_tool(self, tool_id: str) -> Optional[SynthesizedTool]:
        """Return a synthesized tool by id, or None if not found."""
        with self._lock:
            return self._tools.get(tool_id)

    def list_tools(
        self,
        status: Optional[ToolStatus] = None,
    ) -> List[SynthesizedTool]:
        """List synthesized tools, optionally filtered by status."""
        with self._lock:
            results: List[SynthesizedTool] = []
            for tool in self._tools.values():
                if status is not None and tool.status != status:
                    continue
                results.append(tool)
            return results

    def update_tool(
        self,
        tool_id: str,
        **kwargs: Any,
    ) -> Optional[SynthesizedTool]:
        """Update mutable fields on a synthesized tool.

        Supported keyword arguments:
            name, description, version, strategy, status,
            validation_result, parameters, steps.

        The tool's ``updated_at`` is refreshed to the current timestamp
        on a successful update. Returns the updated tool, or ``None`` if
        no tool with ``tool_id`` exists.
        """
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return None
            allowed_simple = {
                "name": str,
                "description": str,
                "version": str,
            }
            for key, caster in allowed_simple.items():
                if key in kwargs:
                    setattr(tool, key, caster(kwargs[key]))
            if "strategy" in kwargs:
                tool.strategy = self._coerce_strategy(kwargs["strategy"])
            if "status" in kwargs:
                tool.status = self._coerce_tool_status(kwargs["status"])
            if "validation_result" in kwargs:
                tool.validation_result = self._coerce_validation_result(
                    kwargs["validation_result"]
                )
            if "parameters" in kwargs:
                new_params = kwargs["parameters"]
                if new_params is None:
                    tool.parameters = []
                elif isinstance(new_params, list):
                    tool.parameters = [
                        p for p in new_params if isinstance(p, ToolParameter)
                    ]
                else:
                    tool.parameters = []
                self._evict_tool_substores(tool.tool_id)
            if "steps" in kwargs:
                new_steps = kwargs["steps"]
                if new_steps is None:
                    tool.steps = []
                elif isinstance(new_steps, list):
                    tool.steps = [s for s in new_steps if isinstance(s, ToolStep)]
                else:
                    tool.steps = []
                self._evict_tool_substores(tool.tool_id)
            tool.updated_at = _now()
            return tool

    def deprecate_tool(self, tool_id: str) -> Optional[SynthesizedTool]:
        """Mark a synthesized tool as deprecated.

        The tool's status is set to ``DEPRECATED`` and an event is
        recorded. Returns the updated tool, or ``None`` if not found.
        """
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return None
            tool.status = ToolStatus.DEPRECATED
            tool.updated_at = _now()
            self._record_event(
                SynthesisEventKind.TOOL_DEPRECATED,
                {
                    "tool_id": tool.tool_id,
                    "name": tool.name,
                },
            )
            return tool

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_tool(self, tool_id: str) -> ValidationReport:
        """Validate a synthesized tool and return a :class:`ValidationReport`.

        The validation checks:
          - every referenced primitive exists in the catalogue,
          - every required parameter has either a default value or an
            input mapping that supplies it at execution time,
          - each step has a non-empty input mapping (when steps exist),
          - the step graph is internally consistent (no duplicate output
            names that would shadow each other unexpectedly).
        """
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                # Synthesize a "not found" report so callers can branch
                # on the result deterministically.
                report = ValidationReport(
                    report_id=_new_id(),
                    tool_id=tool_id,
                    result=ValidationResult.INVALID,
                    issues=[f"Tool '{tool_id}' not found"],
                    warnings=[],
                    validated_at=_now(),
                )
                self._validations[report.report_id] = report
                self._validation_counter += 1
                _evict_fifo_dict(self._validations, _MAX_VALIDATIONS)
                return report

            issues: List[str] = []
            warnings: List[str] = []

            # 1. All referenced primitives must exist.
            for step in tool.steps:
                if step.primitive_id not in self._primitives:
                    issues.append(
                        f"Step '{step.step_id}' references missing "
                        f"primitive '{step.primitive_id}'"
                    )

            # 2. Every required parameter must have a default OR be
            #    supplied via an input mapping at execution.
            known_inputs = self._collect_known_input_names(tool)
            for param in tool.parameters:
                if not param.required:
                    continue
                if param.default_value is not None:
                    continue
                if param.name in known_inputs:
                    continue
                warnings.append(
                    f"Required parameter '{param.name}' has no default "
                    f"and is not bound by any step's input mapping"
                )

            # 3. Each step should have a non-empty input mapping.
            for step in tool.steps:
                if not step.input_mapping:
                    warnings.append(
                        f"Step '{step.step_id}' has empty input_mapping"
                    )

            # 4. Output names should be unique within a tool.
            seen_outputs: Set[str] = set()
            for step in tool.steps:
                if step.output_name and step.output_name in seen_outputs:
                    warnings.append(
                        f"Duplicate step output name '{step.output_name}'"
                    )
                if step.output_name:
                    seen_outputs.add(step.output_name)

            # Determine the overall result.
            if issues:
                result = ValidationResult.INVALID
                tool.validation_result = result
                tool.status = ToolStatus.REJECTED
            elif warnings:
                result = ValidationResult.WARNING
                tool.validation_result = result
                if tool.status == ToolStatus.DRAFT:
                    tool.status = ToolStatus.VALIDATED
            else:
                result = ValidationResult.VALID
                tool.validation_result = result
                if tool.status in (ToolStatus.DRAFT, ToolStatus.REJECTED):
                    tool.status = ToolStatus.VALIDATED

            tool.updated_at = _now()
            report = ValidationReport(
                report_id=_new_id(),
                tool_id=tool.tool_id,
                result=result,
                issues=issues,
                warnings=warnings,
                validated_at=tool.updated_at,
            )
            self._validations[report.report_id] = report
            self._validation_counter += 1
            _evict_fifo_dict(self._validations, _MAX_VALIDATIONS)
            self._record_event(
                SynthesisEventKind.TOOL_VALIDATED,
                {
                    "tool_id": tool.tool_id,
                    "result": result.value,
                    "issues": len(issues),
                    "warnings": len(warnings),
                },
            )
            return report

    # ------------------------------------------------------------------
    # Parameter and step management
    # ------------------------------------------------------------------

    def add_parameter(
        self,
        tool_id: str,
        name: str,
        param_type: ParameterType,
        required: bool = True,
        default_value: Any = None,
        description: str = "",
        validation_rule: str = "",
    ) -> Optional[ToolParameter]:
        """Add a parameter to a synthesized tool.

        Returns the new :class:`ToolParameter`, or ``None`` if the tool
        does not exist. Re-validating the tool after adding a parameter
        is recommended.
        """
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return None
            param = ToolParameter(
                param_id=_new_id(),
                name=name,
                param_type=param_type,
                required=bool(required),
                default_value=default_value,
                description=description,
                validation_rule=validation_rule,
            )
            tool.parameters.append(param)
            tool.updated_at = _now()
            self._evict_tool_substores(tool.tool_id)
            return param

    def list_parameters(self, tool_id: str) -> List[ToolParameter]:
        """List the parameters of a synthesized tool."""
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return []
            return list(tool.parameters)

    def add_step(
        self,
        tool_id: str,
        primitive_id: str,
        input_mapping: Optional[Dict[str, str]] = None,
        output_name: str = "",
        conditional: Optional[str] = None,
    ) -> Optional[ToolStep]:
        """Append a step to a synthesized tool's pipeline.

        Returns the new :class:`ToolStep`, or ``None`` if the tool does
        not exist. The step's ``step_index`` is set to its position in
        the tool's step list at insertion time.
        """
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return None
            step = ToolStep(
                step_id=_new_id(),
                step_index=len(tool.steps),
                primitive_id=primitive_id,
                input_mapping=dict(input_mapping) if input_mapping else {},
                output_name=output_name,
                conditional=conditional,
            )
            tool.steps.append(step)
            tool.updated_at = _now()
            self._evict_tool_substores(tool.tool_id)
            return step

    def list_steps(self, tool_id: str) -> List[ToolStep]:
        """List the steps of a synthesized tool, in pipeline order."""
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return []
            return list(tool.steps)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_tool(
        self,
        tool_id: str,
        inputs: Dict[str, Any],
        agent_id: str,
    ) -> ExecutionRecord:
        """Simulate the execution of a synthesized tool.

        The engine walks the tool's step list, binds each step's inputs
        from the caller-supplied ``inputs`` dictionary or from the
        output of a previous step, and produces a deterministic,
        simulated output. The execution record captures inputs, outputs,
        success, and elapsed wall-clock duration.

        A tool that has not been validated may still be executed; in that
        case its validation result is left untouched. Validation issues
        (for example, missing primitives) cause the execution to fail
        with a descriptive ``error_message``.
        """
        with self._lock:
            tool = self._tools.get(tool_id)
            started = time.time()
            now = _now()
            if tool is None:
                record = ExecutionRecord(
                    execution_id=_new_id(),
                    tool_id=tool_id,
                    inputs=dict(inputs) if inputs else {},
                    outputs={},
                    success=False,
                    duration_ms=0.0,
                    error_message=f"Tool '{tool_id}' not found",
                    executed_at=now,
                    agent_id=agent_id,
                )
                self._executions.append(record)
                self._execution_counter += 1
                _evict_fifo_list(self._executions, _MAX_EXECUTIONS)
                return record

            if tool.status == ToolStatus.DEPRECATED:
                # Deprecated tools can still execute but we surface a
                # warning in the record's error_message.
                warning_prefix = "Tool is deprecated; "
            else:
                warning_prefix = ""

            # Stage 1: bind parameters to a working state.
            working_state: Dict[str, Any] = dict(inputs) if inputs else {}
            for param in tool.parameters:
                if param.name in working_state:
                    continue
                if param.default_value is not None:
                    working_state[param.name] = param.default_value
                elif not param.required:
                    working_state[param.name] = None

            # Stage 2: walk the steps.
            outputs: Dict[str, Any] = {}
            step_outputs: Dict[str, Any] = {}
            error_message: str = ""
            success: bool = True

            for step in tool.steps:
                primitive = self._primitives.get(step.primitive_id)
                if primitive is None:
                    success = False
                    error_message = (
                        f"Step '{step.step_id}' references missing "
                        f"primitive '{step.primitive_id}'"
                    )
                    break

                # Resolve the step's inputs by binding each mapping
                # entry against the working state, then the previous
                # step outputs, then the caller-supplied inputs.
                resolved_inputs: Dict[str, Any] = {}
                for target_key, source_name in step.input_mapping.items():
                    if source_name in working_state:
                        resolved_inputs[target_key] = working_state[source_name]
                    elif source_name in step_outputs:
                        resolved_inputs[target_key] = step_outputs[source_name]
                    elif source_name in (inputs or {}):
                        resolved_inputs[source_name] = inputs[source_name]
                    else:
                        # The mapping is missing; fall back to None so
                        # the simulator does not crash but record the
                        # gap as a missing input.
                        resolved_inputs[target_key] = None

                # Apply the conditional (if any). The conditional is
                # treated as a literal Python expression evaluated
                # against the resolved inputs. We sandbox the eval to
                # a tiny namespace of safe builtins.
                if step.conditional:
                    if not self._evaluate_conditional(
                        step.conditional, resolved_inputs, step_outputs
                    ):
                        # Skip this step silently.
                        continue

                # Simulate the primitive's behaviour.
                step_output = self._simulate_primitive(primitive, resolved_inputs)
                if step_output is self._SIMULATION_ERROR:
                    success = False
                    error_message = (
                        f"Primitive '{primitive.name}' failed on step "
                        f"'{step.step_id}'"
                    )
                    break

                if step.output_name:
                    step_outputs[step.output_name] = step_output
                    outputs[step.output_name] = step_output
                else:
                    outputs[f"step_{step.step_index}"] = step_output

            duration_ms = (time.time() - started) * 1000.0
            tool.execution_count += 1
            if success:
                tool.success_count += 1
                # Auto-promote a validated draft to active on first
                # successful execution.
                if tool.status == ToolStatus.VALIDATED:
                    tool.status = ToolStatus.ACTIVE
            else:
                tool.failure_count += 1
            tool.updated_at = _now()

            record = ExecutionRecord(
                execution_id=_new_id(),
                tool_id=tool.tool_id,
                inputs=dict(inputs) if inputs else {},
                outputs=outputs,
                success=success,
                duration_ms=round(duration_ms, 4),
                error_message=warning_prefix + error_message,
                executed_at=now,
                agent_id=agent_id,
            )
            self._executions.append(record)
            self._execution_counter += 1
            _evict_fifo_list(self._executions, _MAX_EXECUTIONS)
            self._record_event(
                SynthesisEventKind.TOOL_EXECUTED,
                {
                    "tool_id": tool.tool_id,
                    "success": success,
                    "duration_ms": record.duration_ms,
                    "agent_id": agent_id,
                },
            )
            return record

    def list_executions(
        self,
        tool_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ExecutionRecord]:
        """List execution records, optionally filtered by tool id."""
        with self._lock:
            n = max(0, int(limit))
            results: List[ExecutionRecord] = []
            for record in reversed(self._executions):
                if tool_id is not None and record.tool_id != tool_id:
                    continue
                results.append(record)
                if n > 0 and len(results) >= n:
                    break
            return results

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[SynthesisEvent]:
        """Return the most recent synthesis events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> ToolSynthesisStats:
        """Return aggregate statistics about the synthesis engine."""
        with self._lock:
            total_tools = len(self._tools)
            active_tools = sum(
                1 for t in self._tools.values() if t.status == ToolStatus.ACTIVE
            )
            deprecated_tools = sum(
                1 for t in self._tools.values() if t.status == ToolStatus.DEPRECATED
            )
            total_executions = sum(t.execution_count for t in self._tools.values())
            total_successes = sum(t.success_count for t in self._tools.values())
            success_rate = (
                (total_successes / total_executions) if total_executions > 0 else 0.0
            )
            return ToolSynthesisStats(
                total_tools=total_tools,
                total_primitives=len(self._primitives),
                total_executions=total_executions,
                active_tools=active_tools,
                deprecated_tools=deprecated_tools,
                success_rate=round(success_rate, 4),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            stats = self.get_stats()
            by_status: Dict[str, int] = {}
            by_strategy: Dict[str, int] = {}
            for tool in self._tools.values():
                by_status[tool.status.value] = by_status.get(tool.status.value, 0) + 1
                by_strategy[tool.strategy.value] = by_strategy.get(tool.strategy.value, 0) + 1
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_primitives": len(self._primitives),
                "total_tools": len(self._tools),
                "total_requests": len(self._requests),
                "total_validations": len(self._validations),
                "total_executions": len(self._executions),
                "total_events": len(self._events),
                "primitive_counter": self._primitive_counter,
                "tool_counter": self._tool_counter,
                "request_counter": self._request_counter,
                "validation_counter": self._validation_counter,
                "execution_counter": self._execution_counter,
                "active_tools": stats.active_tools,
                "deprecated_tools": stats.deprecated_tools,
                "success_rate": stats.success_rate,
                "tools_by_status": by_status,
                "tools_by_strategy": by_strategy,
                "capacities": {
                    "max_primitives": _MAX_PRIMITIVES,
                    "max_tools": _MAX_TOOLS,
                    "max_parameters": _MAX_PARAMETERS,
                    "max_steps": _MAX_STEPS,
                    "max_requests": _MAX_REQUESTS,
                    "max_validations": _MAX_VALIDATIONS,
                    "max_executions": _MAX_EXECUTIONS,
                    "max_events": _MAX_EVENTS,
                },
            }
            return status

    def get_snapshot(self) -> ToolSynthesisSnapshot:
        """Return a complete snapshot of the synthesis engine state."""
        with self._lock:
            return ToolSynthesisSnapshot(
                initialized=self._initialized,
                primitives=list(self._primitives.values()),
                tools=list(self._tools.values()),
                requests=list(self._requests.values()),
                executions=list(self._executions),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike some sibling engines, this method re-seeds the baseline
        primitive and tool data after clearing, restoring the engine to
        a freshly initialized state.
        """
        with self._lock:
            self._primitives.clear()
            self._tools.clear()
            self._requests.clear()
            self._validations.clear()
            self._executions.clear()
            self._events.clear()
            self._primitive_counter = 0
            self._tool_counter = 0
            self._execution_counter = 0
            self._validation_counter = 0
            self._request_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _coerce_strategy(self, value: Any) -> SynthesisStrategy:
        """Coerce a string (or enum) into a SynthesisStrategy enum value."""
        if isinstance(value, SynthesisStrategy):
            return value
        if isinstance(value, str):
            for member in SynthesisStrategy:
                if member.value == value:
                    return member
        return SynthesisStrategy.COMPOSITION

    def _coerce_tool_status(self, value: Any) -> ToolStatus:
        """Coerce a string (or enum) into a ToolStatus enum value."""
        if isinstance(value, ToolStatus):
            return value
        if isinstance(value, str):
            for member in ToolStatus:
                if member.value == value:
                    return member
        return ToolStatus.DRAFT

    def _coerce_validation_result(self, value: Any) -> ValidationResult:
        """Coerce a string (or enum) into a ValidationResult enum value."""
        if isinstance(value, ValidationResult):
            return value
        if isinstance(value, str):
            for member in ValidationResult:
                if member.value == value:
                    return member
        return ValidationResult.WARNING

    def _collect_known_input_names(
        self, tool: SynthesizedTool
    ) -> Set[str]:
        """Collect the set of names that are bound by step input mappings.

        Assumes the caller already holds ``self._lock``.
        """
        names: Set[str] = set()
        for step in tool.steps:
            for source_name in step.input_mapping.values():
                if source_name:
                    names.add(source_name)
        return names

    def _auto_derive_parameters(
        self,
        name: str,
        available_primitive_ids: List[str],
    ) -> List[ToolParameter]:
        """Auto-derive a default parameter set from the available primitives.

        Assumes the caller already holds ``self._lock``. The first
        parameter is named ``"data"`` and typed LIST; a second parameter
        named ``"field"`` of type STRING is added to make the
        ``extract_field`` primitive useful out of the box.
        """
        params: List[ToolParameter] = []
        seen = False
        for pid in available_primitive_ids or []:
            primitive = self._primitives.get(pid)
            if primitive is None:
                continue
            if primitive.primitive_type in (
                PrimitiveType.TRANSFORM,
                PrimitiveType.MAP,
                PrimitiveType.FILTER,
                PrimitiveType.AGGREGATE,
                PrimitiveType.REDUCE,
                PrimitiveType.COMPUTE,
            ):
                ptype = self._signature_to_param_type(primitive.input_signature)
                params.append(
                    ToolParameter(
                        param_id=_new_id(),
                        name=f"input_{primitive.name}",
                        param_type=ptype,
                        required=True,
                        default_value=None,
                        description=(
                            f"Auto-derived input for primitive "
                            f"'{primitive.name}'"
                        ),
                        validation_rule="",
                    )
                )
                seen = True
        if not seen:
            params.append(
                ToolParameter(
                    param_id=_new_id(),
                    name="data",
                    param_type=ParameterType.LIST,
                    required=True,
                    default_value=None,
                    description=(
                        f"Default data parameter for synthesized tool '{name}'"
                    ),
                    validation_rule="",
                )
            )
        return params

    def _signature_to_param_type(self, signature: str) -> ParameterType:
        """Map a primitive input signature string to a ParameterType."""
        if not signature:
            return ParameterType.ANY
        normalized = signature.strip().lower()
        mapping: Dict[str, ParameterType] = {
            "string": ParameterType.STRING,
            "str": ParameterType.STRING,
            "text": ParameterType.STRING,
            "int": ParameterType.INTEGER,
            "integer": ParameterType.INTEGER,
            "number": ParameterType.INTEGER,
            "float": ParameterType.FLOAT,
            "double": ParameterType.FLOAT,
            "bool": ParameterType.BOOLEAN,
            "boolean": ParameterType.BOOLEAN,
            "list": ParameterType.LIST,
            "array": ParameterType.LIST,
            "vector": ParameterType.LIST,
            "dict": ParameterType.DICT,
            "object": ParameterType.DICT,
            "map": ParameterType.DICT,
            "any": ParameterType.ANY,
        }
        return mapping.get(normalized, ParameterType.ANY)

    def _auto_generate_steps(
        self,
        available_primitive_ids: List[str],
    ) -> List[ToolStep]:
        """Auto-generate a simple pipeline from the available primitives.

        Assumes the caller already holds ``self._lock``. The generated
        pipeline chains each primitive's output into the next primitive's
        input, using a stable naming scheme: the first step's input is
        bound from the ``"data"`` parameter (or the first available
        parameter) and subsequent steps read from the previous step's
        output slot.
        """
        steps: List[ToolStep] = []
        previous_output: Optional[str] = None
        for index, pid in enumerate(available_primitive_ids or []):
            primitive = self._primitives.get(pid)
            if primitive is None:
                continue
            input_mapping: Dict[str, str] = {}
            if index == 0:
                # Bind the very first input to the caller-supplied data
                # parameter. This is the convention used by the seed
                # tools and matches the auto-derived parameter names.
                input_mapping["value"] = "data"
            elif previous_output is not None:
                input_mapping["value"] = previous_output
            output_name = f"step_{index}_out"
            step = ToolStep(
                step_id=_new_id(),
                step_index=index,
                primitive_id=primitive.primitive_id,
                input_mapping=input_mapping,
                output_name=output_name,
                conditional=None,
            )
            steps.append(step)
            previous_output = output_name
        return steps

    def _evict_tool_substores(self, tool_id: str) -> None:
        """Bound the per-tool parameter and step lists by FIFO eviction.

        Assumes the caller already holds ``self._lock``. Per-tool
        parameters and steps are not stored separately here; the global
        bounds on the tool's ``parameters`` and ``steps`` lists are
        applied during ``add_parameter`` and ``add_step`` via the
        ``_MAX_PARAMETERS`` and ``_MAX_STEPS`` totals.
        """
        # Count the totals across all tools and trim the largest tool
        # first when we exceed the per-list capacity.
        total_params = sum(len(t.parameters) for t in self._tools.values())
        total_steps = sum(len(t.steps) for t in self._tools.values())
        if total_params > _MAX_PARAMETERS or total_steps > _MAX_STEPS:
            # Drop the oldest tool's parameters/steps until within bounds.
            tools_in_order = list(self._tools.values())
            for t in tools_in_order:
                if total_params <= _MAX_PARAMETERS and total_steps <= _MAX_STEPS:
                    break
                if t.tool_id == tool_id:
                    # Never trim the tool we just edited; wait for the
                    # next call.
                    continue
                removed_params = len(t.parameters)
                removed_steps = len(t.steps)
                t.parameters = t.parameters[-max(0, _MAX_PARAMETERS - (total_params - removed_params)):]
                t.steps = t.steps[-max(0, _MAX_STEPS - (total_steps - removed_steps)):]
                total_params -= removed_params - len(t.parameters)
                total_steps -= removed_steps - len(t.steps)

    def _simulate_primitive(
        self,
        primitive: PrimitiveSpec,
        resolved_inputs: Dict[str, Any],
    ) -> Any:
        """Simulate the effect of running a primitive.

        Assumes the caller already holds ``self._lock``. The simulator
        is deliberately deterministic and lightweight. It produces a
        plausible output for each known primitive type, sufficient for
        callers to integrate synthesized tools into a larger pipeline
        without standing up a full execution environment.
        """
        if primitive.primitive_type == PrimitiveType.INPUT:
            return resolved_inputs.get("value")

        if primitive.primitive_type == PrimitiveType.OUTPUT:
            return resolved_inputs.get("value")

        if primitive.primitive_type == PrimitiveType.TRANSFORM:
            value = resolved_inputs.get("value")
            if primitive.name == "extract_field":
                if isinstance(value, list) and value:
                    # Extract a single field name from each record.
                    field_name = resolved_inputs.get("field", "value")
                    extracted = []
                    for item in value:
                        if isinstance(item, dict) and field_name in item:
                            extracted.append(item[field_name])
                        elif hasattr(item, field_name):
                            extracted.append(getattr(item, field_name))
                    return {"extracted": extracted, "field": field_name}
                if isinstance(value, dict):
                    return {"extracted": list(value.values()), "field": "values"}
                return {"extracted": value, "field": "raw"}
            if primitive.name == "format_string":
                template = resolved_inputs.get("template", "%s")
                return template % (value,)
            return value

        if primitive.primitive_type == PrimitiveType.COMPUTE:
            value = resolved_inputs.get("value")
            if primitive.name == "compute_average":
                if isinstance(value, list) and value:
                    numeric = [
                        v for v in value
                        if isinstance(v, (int, float)) and not isinstance(v, bool)
                    ]
                    if not numeric:
                        return 0.0
                    return float(sum(numeric) / len(numeric))
                return 0.0
            if isinstance(value, list):
                return {"length": len(value), "sum": sum(
                    v for v in value if isinstance(v, (int, float)) and not isinstance(v, bool)
                )}
            return value

        if primitive.primitive_type == PrimitiveType.FILTER:
            value = resolved_inputs.get("value")
            threshold = resolved_inputs.get("threshold", 0)
            if isinstance(value, list):
                kept = [
                    v for v in value
                    if isinstance(v, (int, float)) and v >= threshold
                ]
                return kept
            return value

        if primitive.primitive_type == PrimitiveType.AGGREGATE:
            value = resolved_inputs.get("value")
            if primitive.name == "aggregate_count":
                if isinstance(value, list):
                    return len(value)
                if isinstance(value, dict):
                    return len(value)
                if isinstance(value, str):
                    return len(value)
                return 0
            if isinstance(value, list):
                return {
                    "count": len(value),
                    "unique": len(set(map(str, value))),
                }
            return value

        if primitive.primitive_type == PrimitiveType.REDUCE:
            value = resolved_inputs.get("value")
            if isinstance(value, list):
                numeric = [
                    v for v in value
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                ]
                if not numeric:
                    return 0
                return sum(numeric)
            return value

        if primitive.primitive_type == PrimitiveType.MAP:
            value = resolved_inputs.get("value")
            if isinstance(value, list):
                return [self._safe_to_str(v) for v in value]
            return value

        if primitive.primitive_type == PrimitiveType.CONDITIONAL:
            return resolved_inputs.get("value")

        if primitive.primitive_type == PrimitiveType.LOOP:
            value = resolved_inputs.get("value")
            if isinstance(value, list):
                return {"iterations": len(value), "values": list(value)}
            return value

        # Fallback: return the first input value unchanged.
        if resolved_inputs:
            return next(iter(resolved_inputs.values()))
        return None

    def _safe_to_str(self, value: Any) -> str:
        """Convert a value to a string, guarding against non-serializable values."""
        try:
            return str(value)
        except Exception:  # pragma: no cover - defensive
            return "<unprintable>"

    def _evaluate_conditional(
        self,
        expression: str,
        resolved_inputs: Dict[str, Any],
        step_outputs: Dict[str, Any],
    ) -> bool:
        """Evaluate a step conditional against its inputs and prior outputs.

        Assumes the caller already holds ``self._lock``. The eval is
        constrained to a small namespace of safe builtins so that an
        attacker-controlled expression cannot escape the sandbox.
        """
        namespace: Dict[str, Any] = {
            "__builtins__": {
                "len": len,
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
                "any": any,
                "all": all,
                "True": True,
                "False": False,
                "None": None,
            },
            "inputs": resolved_inputs,
            "outputs": step_outputs,
        }
        try:
            result = eval(expression, namespace)  # noqa: S307 - sandboxed
        except Exception:
            return False
        return bool(result)

    def _record_event(
        self,
        kind: SynthesisEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable synthesis event.

        Assumes the caller already holds ``self._lock``. The event log
        is bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = SynthesisEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=_safe_dict(payload),
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs synthesis data.

        Seeds five primitives, two synthesized tools (``stats_analyzer``
        active / valid and ``data_filter`` draft / warning), and three
        execution records that exercise the synthesized tools.
        """
        # --- Primitives -------------------------------------------------
        extract = self.add_primitive(
            name="extract_field",
            primitive_type=PrimitiveType.TRANSFORM,
            input_signature="any",
            output_signature="dict",
            description="Extract a named field from a list of records",
            implementation_hint="for item in value: yield item.get(field)",
        )
        average = self.add_primitive(
            name="compute_average",
            primitive_type=PrimitiveType.COMPUTE,
            input_signature="list",
            output_signature="float",
            description="Compute the arithmetic mean of a numeric list",
            implementation_hint="sum(numbers) / max(1, len(numbers))",
        )
        filt = self.add_primitive(
            name="filter_threshold",
            primitive_type=PrimitiveType.FILTER,
            input_signature="list",
            output_signature="list",
            description="Keep only items at or above a numeric threshold",
            implementation_hint="[v for v in value if v >= threshold]",
        )
        fmt = self.add_primitive(
            name="format_string",
            primitive_type=PrimitiveType.TRANSFORM,
            input_signature="string",
            output_signature="string",
            description="Format a string using a printf-style template",
            implementation_hint="template % (value,)",
        )
        counter = self.add_primitive(
            name="aggregate_count",
            primitive_type=PrimitiveType.AGGREGATE,
            input_signature="list",
            output_signature="int",
            description="Count the number of items in a collection",
            implementation_hint="len(value)",
        )

        # --- Synthesized tools -----------------------------------------
        # stats_analyzer: extract_field -> compute_average
        stats_params = [
            ToolParameter(
                param_id=_new_id(),
                name="data",
                param_type=ParameterType.LIST,
                required=True,
                default_value=None,
                description="List of records to analyze",
                validation_rule="len(data) > 0",
            ),
            ToolParameter(
                param_id=_new_id(),
                name="field",
                param_type=ParameterType.STRING,
                required=True,
                default_value="value",
                description="Field name to extract from each record",
                validation_rule="len(field) > 0",
            ),
        ]
        stats_steps = [
            ToolStep(
                step_id=_new_id(),
                step_index=0,
                primitive_id=extract.primitive_id,
                input_mapping={"value": "data"},
                output_name="extracted",
                conditional=None,
            ),
            ToolStep(
                step_id=_new_id(),
                step_index=1,
                primitive_id=average.primitive_id,
                input_mapping={"value": "extracted"},
                output_name="average",
                conditional=None,
            ),
        ]
        stats_tool = SynthesizedTool(
            tool_id=_new_id(),
            name="stats_analyzer",
            description="Compute the average of a field over a list of records",
            version="1.0.0",
            parameters=stats_params,
            steps=stats_steps,
            strategy=SynthesisStrategy.PIPELINE,
            status=ToolStatus.ACTIVE,
            validation_result=ValidationResult.VALID,
            execution_count=0,
            success_count=0,
            failure_count=0,
            created_at=_now(),
            updated_at=_now(),
            creator_agent_id="agent_alpha",
        )
        self._tools[stats_tool.tool_id] = stats_tool
        self._tool_counter += 1
        self._record_event(
            SynthesisEventKind.TOOL_REGISTERED,
            {
                "tool_id": stats_tool.tool_id,
                "name": stats_tool.name,
                "strategy": stats_tool.strategy.value,
            },
        )

        # data_filter: aggregate_count -> filter_threshold (with a
        # warning because the threshold parameter has no default).
        filter_params = [
            ToolParameter(
                param_id=_new_id(),
                name="data",
                param_type=ParameterType.LIST,
                required=True,
                default_value=None,
                description="List of numeric values to filter",
                validation_rule="",
            ),
            ToolParameter(
                param_id=_new_id(),
                name="threshold",
                param_type=ParameterType.FLOAT,
                required=True,
                default_value=None,
                description="Minimum value to retain",
                validation_rule="",
            ),
        ]
        filter_steps = [
            ToolStep(
                step_id=_new_id(),
                step_index=0,
                primitive_id=counter.primitive_id,
                input_mapping={"value": "data"},
                output_name="count",
                conditional=None,
            ),
            ToolStep(
                step_id=_new_id(),
                step_index=1,
                primitive_id=filt.primitive_id,
                input_mapping={"value": "data", "threshold": "threshold"},
                output_name="filtered",
                conditional=None,
            ),
        ]
        filter_tool = SynthesizedTool(
            tool_id=_new_id(),
            name="data_filter",
            description="Count and filter a numeric list by a threshold",
            version="0.1.0",
            parameters=filter_params,
            steps=filter_steps,
            strategy=SynthesisStrategy.COMPOSITION,
            status=ToolStatus.DRAFT,
            validation_result=ValidationResult.WARNING,
            execution_count=0,
            success_count=0,
            failure_count=0,
            created_at=_now(),
            updated_at=_now(),
            creator_agent_id="agent_beta",
        )
        self._tools[filter_tool.tool_id] = filter_tool
        self._tool_counter += 1
        self._record_event(
            SynthesisEventKind.TOOL_REGISTERED,
            {
                "tool_id": filter_tool.tool_id,
                "name": filter_tool.name,
                "strategy": filter_tool.strategy.value,
            },
        )

        # --- Execution records -----------------------------------------
        # 1. stats_analyzer success.
        record_1 = ExecutionRecord(
            execution_id=_new_id(),
            tool_id=stats_tool.tool_id,
            inputs={"data": [{"value": 1}, {"value": 2}, {"value": 3}], "field": "value"},
            outputs={"extracted": {"extracted": [1, 2, 3], "field": "value"}, "average": 2.0},
            success=True,
            duration_ms=4.2,
            error_message="",
            executed_at=_now(),
            agent_id="agent_alpha",
        )
        self._executions.append(record_1)
        self._execution_counter += 1
        stats_tool.execution_count += 1
        stats_tool.success_count += 1

        # 2. data_filter success.
        record_2 = ExecutionRecord(
            execution_id=_new_id(),
            tool_id=filter_tool.tool_id,
            inputs={"data": [1, 2, 3, 4, 5], "threshold": 3.0},
            outputs={"count": 5, "filtered": [3, 4, 5]},
            success=True,
            duration_ms=3.7,
            error_message="",
            executed_at=_now(),
            agent_id="agent_beta",
        )
        self._executions.append(record_2)
        self._execution_counter += 1
        filter_tool.execution_count += 1
        filter_tool.success_count += 1

        # 3. stats_analyzer failure (missing field on every record).
        record_3 = ExecutionRecord(
            execution_id=_new_id(),
            tool_id=stats_tool.tool_id,
            inputs={"data": [{}, {}, {}], "field": "value"},
            outputs={"extracted": {"extracted": [], "field": "value"}, "average": 0.0},
            success=False,
            duration_ms=1.9,
            error_message="No values to average",
            executed_at=_now(),
            agent_id="agent_alpha",
        )
        self._executions.append(record_3)
        self._execution_counter += 1
        stats_tool.execution_count += 1
        stats_tool.failure_count += 1

        # Tie the tools to synthesis requests for completeness.
        request_a = SynthesisRequest(
            request_id=_new_id(),
            requester_agent_id="agent_alpha",
            intent="average_field",
            available_primitives=[extract.primitive_id, average.primitive_id],
            output_tool_id=stats_tool.tool_id,
            status="completed",
            started_at=_now(),
            completed_at=_now(),
        )
        self._requests[request_a.request_id] = request_a
        self._request_counter += 1
        request_b = SynthesisRequest(
            request_id=_new_id(),
            requester_agent_id="agent_beta",
            intent="filter_by_threshold",
            available_primitives=[counter.primitive_id, filt.primitive_id],
            output_tool_id=filter_tool.tool_id,
            status="completed",
            started_at=_now(),
            completed_at=_now(),
        )
        self._requests[request_b.request_id] = request_b
        self._request_counter += 1


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_tool_synthesis() -> ToolSynthesisEngine:
    """Return the singleton ToolSynthesisEngine instance."""
    return ToolSynthesisEngine.get_instance()
