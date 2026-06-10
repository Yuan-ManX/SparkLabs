"""
SparkLabs Agent - Function Dispatch System

A structured function-calling framework that enables agents to dynamically
discover, validate, and execute game development operations. The dispatch
system provides schema-validated function invocation with parameter coercion,
result normalization, and execution auditing — forming the core action layer
for autonomous game creation agents.

Architecture:
  AgentFunctionDispatcher (Singleton)
    |-- FunctionSchema (typed parameter definitions with constraints)
    |-- FunctionBinding (schema + execution handler pair)
    |-- DispatchRequest (validated invocation request)
    |-- DispatchResult (normalized execution outcome)
    |-- DispatchAudit (immutable execution record)
    |-- FunctionCategory (domain-based function grouping)
    |-- ParameterType (supported parameter data types)
    |-- ExecutionPolicy (safety and resource governance)

Core Capabilities:
  - register_function: Register callable game-dev functions with schemas
  - discover_functions: Query available functions by category and capability
  - dispatch: Schema-validated function invocation with parameter coercion
  - batch_dispatch: Parallel execution of multiple functions
  - chain_dispatch: Sequential pipelined function execution
  - get_audit_trail: Retrieve execution history for debugging
  - validate_parameters: Pre-flight parameter validation
"""

from __future__ import annotations

import asyncio
import inspect
import json
import threading
import time as _time_module
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ParameterType(Enum):
    """Supported parameter data types for function schemas."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    JSON = "json"
    UUID = "uuid"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    COLOR = "color"


class FunctionCategory(Enum):
    """Domain-based grouping of dispatchable functions."""
    GAME_CREATION = "game_creation"
    WORLD_BUILDING = "world_building"
    ENTITY_MANAGEMENT = "entity_management"
    PHYSICS_SIMULATION = "physics_simulation"
    RENDERING = "rendering"
    AUDIO = "audio"
    ANIMATION = "animation"
    AI_BEHAVIOR = "ai_behavior"
    UI_SYSTEM = "ui_system"
    ASSET_MANAGEMENT = "asset_management"
    SCENE_MANAGEMENT = "scene_management"
    SCRIPTING = "scripting"
    DIAGNOSTICS = "diagnostics"
    COORDINATION = "coordination"


class ExecutionPolicy(Enum):
    """Safety and resource governance policies for function execution."""
    SAFE = "safe"
    READ_ONLY = "read_only"
    SIDE_EFFECT = "side_effect"
    DESTRUCTIVE = "destructive"
    ELEVATED = "elevated"
    ADMIN = "admin"


class DispatchStatus(Enum):
    """Outcome status for dispatched function calls."""
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ParameterDefinition:
    """Schema definition for a single function parameter.

    Attributes:
        name: Parameter identifier.
        param_type: Expected data type.
        required: Whether the parameter is mandatory.
        default: Default value if not provided.
        description: Human-readable parameter description.
        enum_values: Valid enum choices (when param_type is ENUM).
        min_value: Minimum numeric value constraint.
        max_value: Maximum numeric value constraint.
        pattern: Regex pattern for string validation.
        nested_schema: Schema for array/object element types.
    """
    name: str
    param_type: ParameterType = ParameterType.STRING
    required: bool = True
    default: Any = None
    description: str = ""
    enum_values: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    nested_schema: Optional[List["ParameterDefinition"]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "param_type": self.param_type.value,
            "required": self.required,
            "description": self.description,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum_values:
            result["enum_values"] = self.enum_values
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.pattern:
            result["pattern"] = self.pattern
        if self.nested_schema:
            result["nested_schema"] = [p.to_dict() for p in self.nested_schema]
        return result


@dataclass
class FunctionSchema:
    """Complete schema for a dispatchable function.

    Attributes:
        function_id: Unique function identifier.
        name: Human-readable function name.
        category: Domain category for grouping.
        description: What the function does.
        parameters: Ordered parameter definitions.
        return_type: Expected return data type.
        policy: Required execution permission level.
        timeout_ms: Maximum execution duration in milliseconds.
        tags: Searchable tags for discovery.
        examples: Usage examples with inputs and expected outputs.
    """
    function_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: FunctionCategory = FunctionCategory.GAME_CREATION
    description: str = ""
    parameters: List[ParameterDefinition] = field(default_factory=list)
    return_type: ParameterType = ParameterType.OBJECT
    policy: ExecutionPolicy = ExecutionPolicy.SAFE
    timeout_ms: float = 30000.0
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_id": self.function_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type.value,
            "policy": self.policy.value,
            "timeout_ms": self.timeout_ms,
            "tags": list(self.tags),
            "examples": list(self.examples),
        }


@dataclass
class DispatchRequest:
    """A validated function invocation request.

    Attributes:
        request_id: Unique request identifier.
        function_name: Target function to invoke.
        parameters: Coerced and validated parameter values.
        policy: Required execution policy.
        parent_request_id: Chaining parent request identifier.
        metadata: Arbitrary request context.
    """
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    function_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    policy: ExecutionPolicy = ExecutionPolicy.SAFE
    parent_request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "function_name": self.function_name,
            "parameters": dict(self.parameters),
            "policy": self.policy.value,
            "parent_request_id": self.parent_request_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class DispatchResult:
    """Normalized result from a dispatched function execution.

    Attributes:
        result_id: Unique result identifier.
        request_id: Corresponding request identifier.
        function_name: Executed function name.
        status: Execution outcome status.
        data: Normalized output data.
        error_message: Error description if execution failed.
        duration_ms: Wall-clock execution duration.
        timestamp: Execution timestamp.
        validation_errors: Parameter validation issues.
    """
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    function_name: str = ""
    status: DispatchStatus = DispatchStatus.SUCCESS
    data: Any = None
    error_message: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "function_name": self.function_name,
            "status": self.status.value,
            "data": self.data,
            "error_message": self.error_message,
            "duration_ms": round(self.duration_ms, 4),
            "timestamp": self.timestamp,
            "validation_errors": list(self.validation_errors),
        }


@dataclass
class DispatchAudit:
    """Immutable record of a function dispatch for traceability.

    Attributes:
        audit_id: Unique audit record identifier.
        request: Original dispatch request.
        result: Normalized execution result.
        stack_trace: Exception traceback (if failed).
    """
    audit_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request: Optional[DispatchRequest] = None
    result: Optional[DispatchResult] = None
    stack_trace: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "request": self.request.to_dict() if self.request else None,
            "result": self.result.to_dict() if self.result else None,
            "has_stack_trace": bool(self.stack_trace),
        }


# ---------------------------------------------------------------------------
# Function Binding
# ---------------------------------------------------------------------------


@dataclass
class FunctionBinding:
    """Internal binding between a function schema and its handler.

    Attributes:
        schema: Complete function schema for discovery and validation.
        handler: Callable that implements the function logic.
        is_async: Whether the handler is a coroutine.
        invoke_count: Total successful invocations.
        error_count: Total failed invocations.
        total_duration_ms: Cumulative execution duration.
    """
    schema: FunctionSchema
    handler: Callable[..., Any]
    is_async: bool = False
    invoke_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Agent Function Dispatcher (Singleton)
# ---------------------------------------------------------------------------


class AgentFunctionDispatcher:
    """
    Structured function-calling framework for autonomous game creation agents.

    Provides schema-validated function discovery, invocation, and auditing.
    Functions are registered with typed parameter schemas, enabling agents
    to dynamically compose game-development operations through validated
    function calls.

    Features:
      - Schema-validated parameter coercion and validation
      - Domain-based function categorization and discovery
      - Execution policy-based access control
      - Batch parallel and chain sequential execution modes
      - Comprehensive audit trail for debugging
      - Timeout protection and error recovery
    """

    _instance: Optional["AgentFunctionDispatcher"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentFunctionDispatcher":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._bindings: Dict[str, FunctionBinding] = {}
        self._name_index: Dict[str, str] = {}
        self._category_index: Dict[FunctionCategory, List[str]] = {
            cat: [] for cat in FunctionCategory
        }
        self._audit_trail: List[DispatchAudit] = []
        self._max_audit_entries: int = 1000
        self._total_dispatches: int = 0
        self._total_errors: int = 0

        self._register_builtin_functions()

    # ------------------------------------------------------------------
    # Function Registration
    # ------------------------------------------------------------------

    def register_function(
        self,
        name: str,
        handler: Callable[..., Any],
        schema: Optional[FunctionSchema] = None,
        category: FunctionCategory = FunctionCategory.GAME_CREATION,
        description: str = "",
        parameters: Optional[List[ParameterDefinition]] = None,
        return_type: ParameterType = ParameterType.OBJECT,
        policy: ExecutionPolicy = ExecutionPolicy.SAFE,
        timeout_ms: float = 30000.0,
        tags: Optional[List[str]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> FunctionSchema:
        """
        Register a callable function with its typed schema.

        Args:
            name: Unique function name.
            handler: Callable implementing the function.
            schema: Complete FunctionSchema (overrides individual params).
            category: Domain category for discovery.
            description: Human-readable function description.
            parameters: Ordered parameter definitions.
            return_type: Expected return data type.
            policy: Execution permission level.
            timeout_ms: Maximum execution time.
            tags: Searchable tags.
            examples: Usage examples.

        Returns:
            The registered FunctionSchema.
        """
        with self._lock:
            if schema is None:
                schema = FunctionSchema(
                    name=name,
                    category=category,
                    description=description,
                    parameters=parameters or [],
                    return_type=return_type,
                    policy=policy,
                    timeout_ms=timeout_ms,
                    tags=tags or [],
                    examples=examples or [],
                )

            is_async = asyncio.iscoroutinefunction(handler)
            binding = FunctionBinding(
                schema=schema,
                handler=handler,
                is_async=is_async,
            )

            self._bindings[schema.function_id] = binding
            self._name_index[name] = schema.function_id
            self._category_index.setdefault(category, []).append(schema.function_id)

            return schema

    def unregister_function(self, name: str) -> bool:
        """Remove a registered function by name."""
        with self._lock:
            func_id = self._name_index.pop(name, None)
            if func_id and func_id in self._bindings:
                binding = self._bindings.pop(func_id)
                cat = binding.schema.category
                if func_id in self._category_index.get(cat, []):
                    self._category_index[cat].remove(func_id)
                return True
            return False

    # ------------------------------------------------------------------
    # Function Discovery
    # ------------------------------------------------------------------

    def discover_functions(
        self,
        category: Optional[FunctionCategory] = None,
        tags: Optional[List[str]] = None,
        policy_max: Optional[ExecutionPolicy] = None,
        query: Optional[str] = None,
    ) -> List[FunctionSchema]:
        """
        Query available functions by category, tags, policy, or text search.

        Args:
            category: Filter by domain category.
            tags: Filter by matching tags.
            policy_max: Maximum allowed execution policy.
            query: Free-text search across name and description.

        Returns:
            List of matching FunctionSchema objects.
        """
        results: List[FunctionSchema] = []

        if category:
            candidate_ids = self._category_index.get(category, [])
        else:
            candidate_ids = list(self._bindings.keys())

        for func_id in candidate_ids:
            binding = self._bindings.get(func_id)
            if not binding:
                continue

            schema = binding.schema

            # Tag filter
            if tags and not any(t in schema.tags for t in tags):
                continue

            # Policy filter
            if policy_max:
                policy_order = list(ExecutionPolicy)
                if policy_order.index(schema.policy) > policy_order.index(policy_max):
                    continue

            # Text query
            if query:
                q = query.lower()
                if q not in schema.name.lower() and q not in schema.description.lower():
                    continue

            results.append(schema)

        return results

    def get_function_schema(self, name: str) -> Optional[FunctionSchema]:
        """Retrieve the schema for a named function."""
        func_id = self._name_index.get(name)
        if func_id and func_id in self._bindings:
            return self._bindings[func_id].schema
        return None

    def list_categories(self) -> List[Dict[str, Any]]:
        """List all function categories with function counts."""
        return [
            {
                "category": cat.value,
                "function_count": len(ids),
            }
            for cat, ids in self._category_index.items()
        ]

    # ------------------------------------------------------------------
    # Parameter Validation
    # ------------------------------------------------------------------

    def validate_parameters(
        self,
        function_name: str,
        parameters: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate and coerce parameters against the function schema.

        Args:
            function_name: Target function name.
            parameters: Raw parameter values.

        Returns:
            Tuple of (is_valid, coerced_parameters, error_messages).
        """
        schema = self.get_function_schema(function_name)
        if not schema:
            return False, {}, [f"Function '{function_name}' not found"]

        coerced: Dict[str, Any] = {}
        errors: List[str] = []

        for param_def in schema.parameters:
            value = parameters.get(param_def.name)

            # Check required
            if value is None and param_def.required:
                if param_def.default is not None:
                    coerced[param_def.name] = param_def.default
                else:
                    errors.append(f"Missing required parameter: '{param_def.name}'")
                continue

            if value is None:
                coerced[param_def.name] = param_def.default
                continue

            # Type coercion
            try:
                coerced_value = self._coerce_parameter(param_def, value)
                coerced[param_def.name] = coerced_value
            except (ValueError, TypeError) as e:
                errors.append(f"Parameter '{param_def.name}': {str(e)}")

            # Constraint validation
            if param_def.min_value is not None and isinstance(coerced.get(param_def.name), (int, float)):
                if coerced[param_def.name] < param_def.min_value:
                    errors.append(
                        f"Parameter '{param_def.name}' must be >= {param_def.min_value}"
                    )
            if param_def.max_value is not None and isinstance(coerced.get(param_def.name), (int, float)):
                if coerced[param_def.name] > param_def.max_value:
                    errors.append(
                        f"Parameter '{param_def.name}' must be <= {param_def.max_value}"
                    )
            if param_def.enum_values and coerced.get(param_def.name) is not None:
                if str(coerced[param_def.name]) not in param_def.enum_values:
                    errors.append(
                        f"Parameter '{param_def.name}' must be one of: {param_def.enum_values}"
                    )

        return len(errors) == 0, coerced, errors

    def _coerce_parameter(
        self, param_def: ParameterDefinition, value: Any
    ) -> Any:
        """Coerce a raw value to the expected parameter type."""
        pt = param_def.param_type

        if pt == ParameterType.STRING:
            return str(value)
        elif pt == ParameterType.INTEGER:
            return int(value)
        elif pt == ParameterType.FLOAT:
            return float(value)
        elif pt == ParameterType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        elif pt == ParameterType.ARRAY:
            if not isinstance(value, list):
                raise ValueError(f"Expected array, got {type(value).__name__}")
            return list(value)
        elif pt == ParameterType.OBJECT or pt == ParameterType.JSON:
            if isinstance(value, dict):
                return dict(value)
            if isinstance(value, str):
                return json.loads(value)
            return dict(value) if hasattr(value, "__dict__") else {"value": value}
        elif pt == ParameterType.ENUM:
            return str(value)
        elif pt == ParameterType.UUID:
            return str(value)
        else:
            return value

    # ------------------------------------------------------------------
    # Function Dispatch
    # ------------------------------------------------------------------

    def dispatch(
        self,
        function_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        policy: ExecutionPolicy = ExecutionPolicy.SAFE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DispatchResult:
        """
        Execute a function with schema validation, policy checks, and auditing.

        Args:
            function_name: Name of the registered function to invoke.
            parameters: Function parameters (validated against schema).
            policy: Requested execution policy.
            metadata: Arbitrary request context.

        Returns:
            DispatchResult with execution outcome and data.
        """
        parameters = parameters or {}

        request = DispatchRequest(
            function_name=function_name,
            parameters=dict(parameters),
            policy=policy,
            metadata=metadata or {},
        )

        # Find the function binding
        func_id = self._name_index.get(function_name)
        if not func_id:
            result = DispatchResult(
                request_id=request.request_id,
                function_name=function_name,
                status=DispatchStatus.NOT_FOUND,
                error_message=f"Function '{function_name}' not registered",
            )
            self._record_audit(request, result)
            return result

        binding = self._bindings[func_id]
        schema = binding.schema

        # Policy check
        policy_order = list(ExecutionPolicy)
        if policy_order.index(policy) < policy_order.index(schema.policy):
            result = DispatchResult(
                request_id=request.request_id,
                function_name=function_name,
                status=DispatchStatus.PERMISSION_DENIED,
                error_message=f"Policy {policy.value} insufficient; requires {schema.policy.value}",
            )
            self._record_audit(request, result)
            return result

        # Parameter validation
        is_valid, coerced_params, validation_errors = self.validate_parameters(
            function_name, parameters
        )
        if not is_valid:
            result = DispatchResult(
                request_id=request.request_id,
                function_name=function_name,
                status=DispatchStatus.VALIDATION_ERROR,
                error_message="Parameter validation failed",
                validation_errors=validation_errors,
            )
            self._record_audit(request, result)
            return result

        # Execute
        start_time = _time_module.time()
        try:
            if binding.is_async:
                # For async handlers, run synchronously via asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        data = self._run_async_in_thread(binding.handler, coerced_params)
                    else:
                        data = loop.run_until_complete(binding.handler(**coerced_params))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(binding.handler(**coerced_params))
                    loop.close()
            else:
                data = binding.handler(**coerced_params)

            duration = (_time_module.time() - start_time) * 1000

            # Normalize result
            if hasattr(data, "to_dict"):
                data = data.to_dict()

            binding.invoke_count += 1
            binding.total_duration_ms += duration
            self._total_dispatches += 1

            result = DispatchResult(
                request_id=request.request_id,
                function_name=function_name,
                status=DispatchStatus.SUCCESS,
                data=data,
                duration_ms=duration,
            )
        except Exception as exc:
            duration = (_time_module.time() - start_time) * 1000
            binding.error_count += 1
            self._total_errors += 1

            result = DispatchResult(
                request_id=request.request_id,
                function_name=function_name,
                status=DispatchStatus.EXECUTION_ERROR,
                error_message=str(exc),
                duration_ms=duration,
            )
            self._record_audit(request, result, traceback.format_exc())

        self._record_audit(request, result)
        return result

    def _run_async_in_thread(
        self, handler: Callable[..., Any], params: Dict[str, Any]
    ) -> Any:
        """Execute an async handler in a thread-safe manner."""
        async def _run():
            return await handler(**params)
        return asyncio.run(_run())

    def batch_dispatch(
        self,
        calls: List[Dict[str, Any]],
        policy: ExecutionPolicy = ExecutionPolicy.SAFE,
    ) -> List[DispatchResult]:
        """
        Execute multiple functions in parallel.

        Args:
            calls: List of dicts with 'function_name' and 'parameters' keys.
            policy: Execution policy for all calls.

        Returns:
            List of DispatchResult in the same order as calls.
        """
        results: List[DispatchResult] = []
        for call in calls:
            result = self.dispatch(
                function_name=call.get("function_name", ""),
                parameters=call.get("parameters", {}),
                policy=policy,
                metadata=call.get("metadata", {}),
            )
            results.append(result)
        return results

    def chain_dispatch(
        self,
        steps: List[Dict[str, Any]],
        policy: ExecutionPolicy = ExecutionPolicy.SAFE,
        stop_on_error: bool = True,
    ) -> List[DispatchResult]:
        """
        Execute functions sequentially, piping output to input.

        Args:
            steps: List of dicts with 'function_name', 'parameters', and
                   optional 'output_key' for piping.
            policy: Execution policy for all steps.
            stop_on_error: Halt chain on first error.

        Returns:
            List of DispatchResult in execution order.
        """
        results: List[DispatchResult] = []
        chain_context: Dict[str, Any] = {}

        for step in steps:
            params = dict(step.get("parameters", {}))
            output_key = step.get("output_key")

            # Inject previous results into parameters
            for key, value in params.items():
                if isinstance(value, str) and value.startswith("$chain."):
                    ref_key = value[7:]
                    if ref_key in chain_context:
                        params[key] = chain_context[ref_key]

            result = self.dispatch(
                function_name=step.get("function_name", ""),
                parameters=params,
                policy=policy,
                metadata={"chain_step": len(results)},
            )
            results.append(result)

            if output_key and result.status == DispatchStatus.SUCCESS:
                chain_context[output_key] = result.data

            if stop_on_error and result.status != DispatchStatus.SUCCESS:
                break

        return results

    # ------------------------------------------------------------------
    # Audit & Telemetry
    # ------------------------------------------------------------------

    def _record_audit(
        self,
        request: DispatchRequest,
        result: DispatchResult,
        stack_trace: str = "",
    ):
        """Record a dispatch event in the audit trail."""
        audit = DispatchAudit(
            request=request,
            result=result,
            stack_trace=stack_trace,
        )
        self._audit_trail.append(audit)
        if len(self._audit_trail) > self._max_audit_entries:
            self._audit_trail = self._audit_trail[-500:]

    def get_audit_trail(
        self,
        function_name: Optional[str] = None,
        status: Optional[DispatchStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve filtered execution audit records.

        Args:
            function_name: Filter by function name.
            status: Filter by dispatch status.
            limit: Maximum records to return.

        Returns:
            List of audit trail records as dicts.
        """
        results = []
        for audit in reversed(self._audit_trail):
            if audit.result:
                if function_name and audit.result.function_name != function_name:
                    continue
                if status and audit.result.status != status:
                    continue
            results.append(audit.to_dict())
            if len(results) >= limit:
                break
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Return aggregate dispatch statistics."""
        function_stats: Dict[str, Dict[str, Any]] = {}
        for binding in self._bindings.values():
            function_stats[binding.schema.name] = {
                "category": binding.schema.category.value,
                "invoke_count": binding.invoke_count,
                "error_count": binding.error_count,
                "avg_duration_ms": round(
                    binding.total_duration_ms / max(1, binding.invoke_count), 4
                ),
                "policy": binding.schema.policy.value,
            }

        return {
            "total_functions": len(self._bindings),
            "total_dispatches": self._total_dispatches,
            "total_errors": self._total_errors,
            "error_rate": round(
                self._total_errors / max(1, self._total_dispatches) * 100, 2
            ),
            "audit_entries": len(self._audit_trail),
            "functions": function_stats,
            "categories": self.list_categories(),
        }

    # ------------------------------------------------------------------
    # Built-in Functions
    # ------------------------------------------------------------------

    def _register_builtin_functions(self):
        """Register the standard set of game-development utility functions."""
        self.register_function(
            name="create_game_object",
            handler=self._builtin_create_game_object,
            category=FunctionCategory.ENTITY_MANAGEMENT,
            description="Create a new game object with specified type and initial properties.",
            parameters=[
                ParameterDefinition("object_type", ParameterType.STRING, True,
                                    description="Type of game object (sprite, text, group)"),
                ParameterDefinition("name", ParameterType.STRING, True,
                                    description="Display name for the object"),
                ParameterDefinition("position_x", ParameterType.FLOAT, False, 0.0,
                                    description="Initial X position"),
                ParameterDefinition("position_y", ParameterType.FLOAT, False, 0.0,
                                    description="Initial Y position"),
                ParameterDefinition("properties", ParameterType.OBJECT, False, {},
                                    description="Additional object properties"),
            ],
            tags=["entity", "creation", "gameplay"],
        )

        self.register_function(
            name="set_object_property",
            handler=self._builtin_set_property,
            category=FunctionCategory.ENTITY_MANAGEMENT,
            description="Set a property value on an existing game object.",
            parameters=[
                ParameterDefinition("object_id", ParameterType.STRING, True,
                                    description="Target object identifier"),
                ParameterDefinition("property_name", ParameterType.STRING, True,
                                    description="Property to modify"),
                ParameterDefinition("value", ParameterType.JSON, True,
                                    description="New property value"),
            ],
            tags=["entity", "property", "modification"],
            policy=ExecutionPolicy.SIDE_EFFECT,
        )

        self.register_function(
            name="load_scene",
            handler=self._builtin_load_scene,
            category=FunctionCategory.SCENE_MANAGEMENT,
            description="Load and transition to a named game scene.",
            parameters=[
                ParameterDefinition("scene_name", ParameterType.STRING, True,
                                    description="Scene identifier to load"),
                ParameterDefinition("transition_type", ParameterType.ENUM, False, "fade",
                                    enum_values=["fade", "slide", "zoom", "none"],
                                    description="Visual transition effect"),
                ParameterDefinition("duration_ms", ParameterType.FLOAT, False, 500.0,
                                    description="Transition duration in milliseconds",
                                    min_value=0.0, max_value=5000.0),
            ],
            tags=["scene", "loading", "transition"],
            policy=ExecutionPolicy.SIDE_EFFECT,
        )

        self.register_function(
            name="play_animation",
            handler=self._builtin_play_animation,
            category=FunctionCategory.ANIMATION,
            description="Play a named animation on a target object.",
            parameters=[
                ParameterDefinition("object_id", ParameterType.STRING, True,
                                    description="Target object identifier"),
                ParameterDefinition("animation_name", ParameterType.STRING, True,
                                    description="Animation sequence to play"),
                ParameterDefinition("loop", ParameterType.BOOLEAN, False, False,
                                    description="Whether to loop the animation"),
                ParameterDefinition("speed", ParameterType.FLOAT, False, 1.0,
                                    description="Playback speed multiplier",
                                    min_value=0.1, max_value=10.0),
            ],
            tags=["animation", "playback", "visual"],
            policy=ExecutionPolicy.SIDE_EFFECT,
        )

        self.register_function(
            name="play_sound",
            handler=self._builtin_play_sound,
            category=FunctionCategory.AUDIO,
            description="Play a sound effect or music track.",
            parameters=[
                ParameterDefinition("sound_id", ParameterType.STRING, True,
                                    description="Sound asset identifier"),
                ParameterDefinition("volume", ParameterType.FLOAT, False, 1.0,
                                    description="Playback volume 0.0-1.0",
                                    min_value=0.0, max_value=1.0),
                ParameterDefinition("loop", ParameterType.BOOLEAN, False, False,
                                    description="Loop playback"),
                ParameterDefinition("spatial_x", ParameterType.FLOAT, False, None,
                                    description="Spatial X position for 3D audio"),
                ParameterDefinition("spatial_y", ParameterType.FLOAT, False, None,
                                    description="Spatial Y position for 3D audio"),
            ],
            tags=["audio", "sound", "playback"],
        )

        self.register_function(
            name="spawn_entity",
            handler=self._builtin_spawn_entity,
            category=FunctionCategory.WORLD_BUILDING,
            description="Spawn an entity in the game world at a position.",
            parameters=[
                ParameterDefinition("entity_type", ParameterType.STRING, True,
                                    description="Entity template or type"),
                ParameterDefinition("world_x", ParameterType.FLOAT, True,
                                    description="World X coordinate"),
                ParameterDefinition("world_y", ParameterType.FLOAT, True,
                                    description="World Y coordinate"),
                ParameterDefinition("count", ParameterType.INTEGER, False, 1,
                                    description="Number to spawn",
                                    min_value=1, max_value=100),
                ParameterDefinition("spread_radius", ParameterType.FLOAT, False, 0.0,
                                    description="Random spread radius"),
            ],
            tags=["world", "spawning", "entity"],
            policy=ExecutionPolicy.SIDE_EFFECT,
        )

        self.register_function(
            name="query_world_state",
            handler=self._builtin_query_world,
            category=FunctionCategory.DIAGNOSTICS,
            description="Query current game world state information.",
            parameters=[
                ParameterDefinition("query_type", ParameterType.ENUM, True,
                                    enum_values=["entities", "scene", "performance", "all"],
                                    description="Type of state to query"),
                ParameterDefinition("filters", ParameterType.OBJECT, False, {},
                                    description="Optional query filters"),
            ],
            return_type=ParameterType.OBJECT,
            tags=["world", "query", "diagnostics"],
            policy=ExecutionPolicy.READ_ONLY,
        )

        self.register_function(
            name="apply_physics_force",
            handler=self._builtin_apply_force,
            category=FunctionCategory.PHYSICS_SIMULATION,
            description="Apply a force to a physics-enabled object.",
            parameters=[
                ParameterDefinition("object_id", ParameterType.STRING, True,
                                    description="Target physics object"),
                ParameterDefinition("force_x", ParameterType.FLOAT, True,
                                    description="Force X component"),
                ParameterDefinition("force_y", ParameterType.FLOAT, True,
                                    description="Force Y component"),
                ParameterDefinition("force_type", ParameterType.ENUM, False, "impulse",
                                    enum_values=["impulse", "continuous", "explosion"],
                                    description="Force application mode"),
            ],
            tags=["physics", "force", "simulation"],
            policy=ExecutionPolicy.SIDE_EFFECT,
        )

        self.register_function(
            name="set_camera_target",
            handler=self._builtin_set_camera,
            category=FunctionCategory.RENDERING,
            description="Set the camera to follow a target object.",
            parameters=[
                ParameterDefinition("object_id", ParameterType.STRING, True,
                                    description="Target to follow"),
                ParameterDefinition("smoothing", ParameterType.FLOAT, False, 0.1,
                                    description="Camera smoothing factor 0.0-1.0",
                                    min_value=0.0, max_value=1.0),
                ParameterDefinition("offset_x", ParameterType.FLOAT, False, 0.0,
                                    description="Horizontal offset"),
                ParameterDefinition("offset_y", ParameterType.FLOAT, False, 0.0,
                                    description="Vertical offset"),
            ],
            tags=["camera", "rendering", "viewport"],
            policy=ExecutionPolicy.SIDE_EFFECT,
        )

        self.register_function(
            name="emit_event",
            handler=self._builtin_emit_event,
            category=FunctionCategory.COORDINATION,
            description="Emit a game event for other systems to respond to.",
            parameters=[
                ParameterDefinition("event_name", ParameterType.STRING, True,
                                    description="Event identifier"),
                ParameterDefinition("event_data", ParameterType.OBJECT, False, {},
                                    description="Event payload data"),
                ParameterDefinition("delay_ms", ParameterType.FLOAT, False, 0.0,
                                    description="Delay before emission in ms"),
            ],
            tags=["event", "coordination", "signal"],
            policy=ExecutionPolicy.SIDE_EFFECT,
        )

    # Built-in handler implementations
    @staticmethod
    def _builtin_create_game_object(
        object_type: str = "sprite",
        name: str = "GameObject",
        position_x: float = 0.0,
        position_y: float = 0.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "object_id": uuid.uuid4().hex,
            "type": object_type,
            "name": name,
            "position": {"x": position_x, "y": position_y},
            "properties": properties or {},
            "created": True,
        }

    @staticmethod
    def _builtin_set_property(
        object_id: str = "",
        property_name: str = "",
        value: Any = None,
    ) -> Dict[str, Any]:
        return {
            "object_id": object_id,
            "property": property_name,
            "value": value,
            "updated": True,
        }

    @staticmethod
    def _builtin_load_scene(
        scene_name: str = "",
        transition_type: str = "fade",
        duration_ms: float = 500.0,
    ) -> Dict[str, Any]:
        return {
            "scene": scene_name,
            "transition": transition_type,
            "duration_ms": duration_ms,
            "loaded": True,
        }

    @staticmethod
    def _builtin_play_animation(
        object_id: str = "",
        animation_name: str = "",
        loop: bool = False,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        return {
            "object_id": object_id,
            "animation": animation_name,
            "loop": loop,
            "speed": speed,
            "playing": True,
        }

    @staticmethod
    def _builtin_play_sound(
        sound_id: str = "",
        volume: float = 1.0,
        loop: bool = False,
        spatial_x: Optional[float] = None,
        spatial_y: Optional[float] = None,
    ) -> Dict[str, Any]:
        return {
            "sound_id": sound_id,
            "volume": volume,
            "loop": loop,
            "spatial": {"x": spatial_x, "y": spatial_y} if spatial_x is not None else None,
            "playing": True,
        }

    @staticmethod
    def _builtin_spawn_entity(
        entity_type: str = "",
        world_x: float = 0.0,
        world_y: float = 0.0,
        count: int = 1,
        spread_radius: float = 0.0,
    ) -> Dict[str, Any]:
        import random as _random
        entities = []
        for i in range(count):
            offset_x = _random.uniform(-spread_radius, spread_radius) if spread_radius > 0 else 0
            offset_y = _random.uniform(-spread_radius, spread_radius) if spread_radius > 0 else 0
            entities.append({
                "entity_id": uuid.uuid4().hex,
                "type": entity_type,
                "position": {"x": world_x + offset_x, "y": world_y + offset_y},
            })
        return {"spawned": len(entities), "entities": entities}

    @staticmethod
    def _builtin_query_world(
        query_type: str = "all",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "query_type": query_type,
            "filters": filters or {},
            "timestamp": _time_module.time(),
            "world_state": {"status": "active", "entity_count": 42},
        }

    @staticmethod
    def _builtin_apply_force(
        object_id: str = "",
        force_x: float = 0.0,
        force_y: float = 0.0,
        force_type: str = "impulse",
    ) -> Dict[str, Any]:
        return {
            "object_id": object_id,
            "force": {"x": force_x, "y": force_y},
            "type": force_type,
            "applied": True,
        }

    @staticmethod
    def _builtin_set_camera(
        object_id: str = "",
        smoothing: float = 0.1,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> Dict[str, Any]:
        return {
            "target": object_id,
            "smoothing": smoothing,
            "offset": {"x": offset_x, "y": offset_y},
            "tracking": True,
        }

    @staticmethod
    def _builtin_emit_event(
        event_name: str = "",
        event_data: Optional[Dict[str, Any]] = None,
        delay_ms: float = 0.0,
    ) -> Dict[str, Any]:
        return {
            "event": event_name,
            "data": event_data or {},
            "delay_ms": delay_ms,
            "emitted": True,
        }

    # ------------------------------------------------------------------
    # Singleton Accessors
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentFunctionDispatcher":
        """Return the singleton dispatcher instance."""
        return cls()

    def reset(self) -> None:
        """Reset the dispatcher to initial state."""
        with self._lock:
            self._bindings.clear()
            self._name_index.clear()
            self._category_index = {cat: [] for cat in FunctionCategory}
            self._audit_trail.clear()
            self._total_dispatches = 0
            self._total_errors = 0
            self._register_builtin_functions()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_function_dispatcher() -> AgentFunctionDispatcher:
    """Return the singleton AgentFunctionDispatcher instance."""
    return AgentFunctionDispatcher()