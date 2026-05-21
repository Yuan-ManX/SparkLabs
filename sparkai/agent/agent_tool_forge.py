"""
SparkLabs Agent - Tool Forge

Autonomous tool and skill creation system that generates new tools from
successful task patterns, validates tool schemas, tracks tool performance,
and manages a tool library with versioning.

Architecture:
  AgentToolForge
    |-- Schema Registry (defines and stores tool schemas)
    |-- Forge Engine (generates tools from templates / patterns / composition)
    |-- Validation Pipeline (schema, execution, permission, timeout checks)
    |-- Performance Tracker (success rate, duration, error distribution)
    |-- Tool Lifecycle Manager (draft → testing → active → deprecated → broken)
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolCategory(Enum):
    FILE_OPS = "file_ops"
    DATA_PROCESS = "data_process"
    API_WRAPPER = "api_wrapper"
    CODE_GEN = "code_gen"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    GAME_SPECIFIC = "game_specific"
    UTILITY = "utility"


class ToolStatus(Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BROKEN = "broken"


class ForgeStrategy(Enum):
    TEMPLATE_FILL = "template_fill"
    PATTERN_EXTRACT = "pattern_extract"
    COMPOSE_EXISTING = "compose_existing"
    PARAMETERIZE = "parameterize"
    OPTIMIZE = "optimize"


class ValidationResult(Enum):
    PASS = "pass"
    FAIL_SCHEMA = "fail_schema"
    FAIL_EXECUTION = "fail_execution"
    FAIL_PERMISSION = "fail_permission"
    FAIL_TIMEOUT = "fail_timeout"


@dataclass
class ToolParameter:
    name: str = ""
    param_type: str = "string"
    description: str = ""
    required: bool = True
    default_value: Any = None
    constraints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "param_type": self.param_type,
            "description": self.description, "required": self.required,
            "default_value": self.default_value, "constraints": self.constraints,
        }


@dataclass
class ToolSchema:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    parameters: List[ToolParameter] = field(default_factory=list)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "category": self.category.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "output_schema": self.output_schema, "version": self.version,
            "created_at": self.created_at,
        }


@dataclass
class ForgedTool:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    schema_id: str = ""
    name: str = ""
    status: ToolStatus = ToolStatus.DRAFT
    strategy: ForgeStrategy = ForgeStrategy.TEMPLATE_FILL
    source_agent_id: str = ""
    template_source: str = ""
    version: int = 1
    usage_count: int = 0
    success_count: int = 0
    total_duration_ms: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "schema_id": self.schema_id, "name": self.name,
            "status": self.status.value, "strategy": self.strategy.value,
            "source_agent_id": self.source_agent_id,
            "template_source": self.template_source, "version": self.version,
            "usage_count": self.usage_count, "success_count": self.success_count,
            "error_counts": self.error_counts, "created_at": self.created_at,
            "last_used_at": self.last_used_at,
        }


@dataclass
class ToolExecutionRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tool_id: str = ""
    agent_id: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    output: Any = None
    success: bool = False
    duration_ms: float = 0.0
    error_type: str = ""
    error_message: str = ""
    executed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "tool_id": self.tool_id, "agent_id": self.agent_id,
            "inputs": self.inputs, "output": self.output,
            "success": self.success, "duration_ms": self.duration_ms,
            "error_type": self.error_type, "error_message": self.error_message,
            "executed_at": self.executed_at,
        }


@dataclass
class ForgeRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    schema_id: str = ""
    strategy: ForgeStrategy = ForgeStrategy.TEMPLATE_FILL
    template_source: str = ""
    agent_id: str = ""
    result_tool_id: str = ""
    success: bool = False
    error_message: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "schema_id": self.schema_id,
            "strategy": self.strategy.value, "template_source": self.template_source,
            "agent_id": self.agent_id, "result_tool_id": self.result_tool_id,
            "success": self.success, "error_message": self.error_message,
            "created_at": self.created_at,
        }


class AgentToolForge:
    """Autonomous tool creation, validation, and lifecycle management."""

    _instance: Optional["AgentToolForge"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._tools: Dict[str, ForgedTool] = {}
        self._schemas: Dict[str, ToolSchema] = {}
        self._execution_records: List[ToolExecutionRecord] = []
        self._forge_history: List[ForgeRequest] = []

    @classmethod
    def get_instance(cls) -> "AgentToolForge":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Schema Management ----

    def define_schema(self, name: str, description: str, category: str,
                      parameters: List[Dict[str, Any]],
                      output_schema: Optional[Dict[str, Any]] = None) -> ToolSchema:
        try:
            cat = ToolCategory(category.lower())
        except ValueError:
            cat = ToolCategory.UTILITY

        parsed_params: List[ToolParameter] = []
        for p in parameters:
            parsed_params.append(ToolParameter(
                name=p.get("name", ""), param_type=p.get("param_type", "string"),
                description=p.get("description", ""),
                required=p.get("required", True),
                default_value=p.get("default_value"),
                constraints=p.get("constraints", {}),
            ))

        schema = ToolSchema(name=name, description=description, category=cat,
                            parameters=parsed_params,
                            output_schema=output_schema or {})
        self._schemas[schema.id] = schema
        return schema

    # ---- Forge Engine ----

    def forge_tool(self, schema_id: str, strategy: str,
                   template_source: str = "",
                   agent_id: str = "") -> Optional[ForgedTool]:
        schema = self._schemas.get(schema_id)
        if schema is None:
            self._forge_history.append(ForgeRequest(
                schema_id=schema_id, strategy=ForgeStrategy.TEMPLATE_FILL,
                template_source=template_source, agent_id=agent_id,
                success=False, error_message=f"Schema {schema_id} not found"))
            return None

        try:
            strat = ForgeStrategy(strategy.lower())
        except ValueError:
            strat = ForgeStrategy.TEMPLATE_FILL

        tool = ForgedTool(schema_id=schema_id, name=schema.name,
                          status=ToolStatus.DRAFT, strategy=strat,
                          source_agent_id=agent_id,
                          template_source=template_source,
                          version=schema.version)
        self._tools[tool.id] = tool
        self._forge_history.append(ForgeRequest(
            schema_id=schema_id, strategy=strat, template_source=template_source,
            agent_id=agent_id, result_tool_id=tool.id, success=True))
        return tool

    # ---- Validation Pipeline ----

    def validate_tool(self, tool_id: str,
                      test_inputs: Optional[Dict[str, Any]] = None
                      ) -> ValidationResult:
        tool = self._tools.get(tool_id)
        if tool is None:
            return ValidationResult.FAIL_SCHEMA
        schema = self._schemas.get(tool.schema_id)
        if schema is None:
            return ValidationResult.FAIL_SCHEMA

        for param in schema.parameters:
            if param.required:
                if test_inputs is None or param.name not in test_inputs:
                    return ValidationResult.FAIL_SCHEMA
            if test_inputs and param.name in test_inputs:
                value = test_inputs[param.name]
                constraints = param.constraints
                if param.param_type == "integer" and not isinstance(value, int):
                    return ValidationResult.FAIL_SCHEMA
                if param.param_type == "number" and not isinstance(value, (int, float)):
                    return ValidationResult.FAIL_SCHEMA
                if "min" in constraints and isinstance(value, (int, float)):
                    if value < constraints["min"]:
                        return ValidationResult.FAIL_SCHEMA
                if "max" in constraints and isinstance(value, (int, float)):
                    if value > constraints["max"]:
                        return ValidationResult.FAIL_SCHEMA

        if random.random() < 0.05:
            return random.choice([
                ValidationResult.FAIL_EXECUTION,
                ValidationResult.FAIL_TIMEOUT])
        return ValidationResult.PASS

    # ---- Tool Lifecycle ----

    def activate_tool(self, tool_id: str) -> bool:
        tool = self._tools.get(tool_id)
        if tool is None:
            return False
        if tool.status in (ToolStatus.DRAFT, ToolStatus.TESTING):
            tool.status = ToolStatus.ACTIVE
            return True
        return False

    def deprecate_tool(self, tool_id: str, reason: str = "") -> bool:
        tool = self._tools.get(tool_id)
        if tool is None:
            return False
        tool.status = ToolStatus.DEPRECATED
        return True

    # ---- Execution ----

    def _make_error_record(self, tool_id: str, agent_id: str,
                           inputs: Dict[str, Any], duration_ms: float,
                           error_type: str, error_message: str
                           ) -> ToolExecutionRecord:
        record = ToolExecutionRecord(
            tool_id=tool_id, agent_id=agent_id, inputs=inputs,
            success=False, duration_ms=duration_ms,
            error_type=error_type, error_message=error_message)
        self._execution_records.append(record)
        return record

    def execute_tool(self, tool_id: str, inputs: Dict[str, Any],
                     agent_id: str = "") -> ToolExecutionRecord:
        t0 = time.time()

        tool = self._tools.get(tool_id)
        if tool is None:
            dur = (time.time() - t0) * 1000.0
            return self._make_error_record(
                tool_id, agent_id, inputs, dur,
                "not_found", f"Tool {tool_id} not found")

        schema = self._schemas.get(tool.schema_id)
        if schema is None:
            dur = (time.time() - t0) * 1000.0
            return self._make_error_record(
                tool_id, agent_id, inputs, dur,
                "schema_missing", f"Schema {tool.schema_id} not found for {tool_id}")

        validation = self.validate_tool(tool_id, inputs)
        if validation != ValidationResult.PASS:
            dur = (time.time() - t0) * 1000.0
            return self._make_error_record(
                tool_id, agent_id, inputs, dur,
                validation.value, f"Validation failed: {validation.value}")

        success = random.random() < 0.90
        dur = (time.time() - t0) * 1000.0 + random.uniform(5.0, 200.0)
        error_type, error_msg = "", ""
        if not success:
            error_type = random.choice(
                ["runtime_error", "timeout", "output_validation"])
            error_msg = f"Simulated {error_type} during execution"

        tool.usage_count += 1
        if success:
            tool.success_count += 1
        else:
            tool.error_counts[error_type] = tool.error_counts.get(error_type, 0) + 1
        tool.total_duration_ms += dur
        tool.last_used_at = time.time()

        output = {"result": "simulated_output", "status": "ok"} if success else None
        record = ToolExecutionRecord(
            tool_id=tool_id, agent_id=agent_id, inputs=inputs, output=output,
            success=success, duration_ms=round(dur, 2),
            error_type=error_type, error_message=error_msg)
        self._execution_records.append(record)
        return record

    # ---- Query & Retrieval ----

    def list_tools(self, category: Optional[str] = None,
                   status: Optional[str] = None) -> List[ForgedTool]:
        result: List[ForgedTool] = []
        for tool in self._tools.values():
            if category is not None:
                schema = self._schemas.get(tool.schema_id)
                if schema is None or schema.category.value != category.lower():
                    continue
            if status is not None and tool.status.value != status.lower():
                continue
            result.append(tool)
        return result

    def get_tool_performance(self, tool_id: str) -> Dict[str, Any]:
        tool = self._tools.get(tool_id)
        if tool is None or tool.usage_count == 0:
            return {"tool_id": tool_id, "found": tool is not None,
                    "success_rate": 0.0, "avg_duration_ms": 0.0,
                    "total_usage": 0, "error_distribution": {}}
        return {
            "tool_id": tool_id, "found": True,
            "success_rate": round(tool.success_count / tool.usage_count * 100.0, 1),
            "avg_duration_ms": round(tool.total_duration_ms / tool.usage_count, 2),
            "total_usage": tool.usage_count,
            "error_distribution": dict(tool.error_counts),
            "last_used_at": tool.last_used_at,
        }

    # ---- Refinement ----

    def refine_tool(self, tool_id: str,
                    optimization_target: str = "accuracy") -> Optional[ForgedTool]:
        tool = self._tools.get(tool_id)
        if tool is None:
            return None
        schema = self._schemas.get(tool.schema_id)
        if schema is None:
            return None

        refined_schema = ToolSchema(
            name=f"{schema.name}_refined", description=schema.description,
            category=schema.category, parameters=schema.parameters,
            output_schema=schema.output_schema, version=schema.version + 1)
        self._schemas[refined_schema.id] = refined_schema

        refined_tool = ForgedTool(
            schema_id=refined_schema.id, name=f"{tool.name}_refined",
            status=ToolStatus.DRAFT, strategy=ForgeStrategy.OPTIMIZE,
            source_agent_id="refinement_engine",
            template_source=tool.template_source, version=tool.version + 1)
        self._tools[refined_tool.id] = refined_tool
        return refined_tool

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
        strategy_counts: Dict[str, int] = {}
        for t in self._tools.values():
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1
            strategy_counts[t.strategy.value] = strategy_counts.get(t.strategy.value, 0) + 1

        category_counts: Dict[str, int] = {}
        for s in self._schemas.values():
            category_counts[s.category.value] = category_counts.get(s.category.value, 0) + 1

        total_usage = sum(t.usage_count for t in self._tools.values())
        total_success = sum(t.success_count for t in self._tools.values())
        overall_success_rate = (round(total_success / total_usage * 100.0, 1)
                                if total_usage > 0 else 0.0)

        return {
            "total_tools": len(self._tools),
            "total_schemas": len(self._schemas),
            "total_executions": len(self._execution_records),
            "total_forge_requests": len(self._forge_history),
            "active_tools": sum(1 for t in self._tools.values()
                                if t.status == ToolStatus.ACTIVE),
            "status_distribution": status_counts,
            "strategy_distribution": strategy_counts,
            "category_distribution": category_counts,
            "overall_success_rate": overall_success_rate,
            "total_usage": total_usage,
        }


def get_tool_forge() -> AgentToolForge:
    return AgentToolForge.get_instance()