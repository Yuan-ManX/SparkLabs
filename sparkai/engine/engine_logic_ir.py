"""
SparkLabs Engine - Logic IR

Logic-as-data intermediate representation for LLM-friendly game logic
authoring. Game logic is expressed as a graph of typed IR nodes (conditions,
actions, events, variables, functions, branches, loops, assignments) that
can be validated, serialized, and executed against a runtime context.

Architecture:
  LogicIRSystem (Singleton)
    |-- IRNodeType (categories of IR nodes)
    |-- IRNode    (a single node in the logic graph)
    |-- IREvent   (a named event with conditions and actions)
    |-- LogicIR   (a complete logic program composed of events)
    |-- LogicIRSnapshot (immutable snapshot of system state)

Lifecycle:
  1. create_ir(name) -> LogicIR
  2. add_event(ir_id, event) -> IREvent
  3. validate(ir_id) -> Dict
  4. execute(ir_id, context) -> Dict
  5. serialize(ir_id) -> str / deserialize(json_str) -> LogicIR
  6. get_snapshot() -> LogicIRSnapshot
  7. reset() -> None

Usage:
    system = get_logic_ir_system()
    ir = system.create_ir("player_logic")
    event = IREvent(name="on_damage", conditions=[], actions=[])
    system.add_event(ir.ir_id, event)
    report = system.validate(ir.ir_id)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================


class IRNodeType(Enum):
    """Types of nodes in the logic intermediate representation."""
    CONDITION = "condition"
    ACTION = "action"
    EVENT = "event"
    VARIABLE = "variable"
    FUNCTION = "function"
    BRANCH = "branch"
    LOOP = "loop"
    ASSIGN = "assign"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class IRNode:
    """A single node in the logic graph.

    Attributes:
        node_id: Unique identifier (auto-generated).
        node_type: Category of the node.
        name: Human-readable name of the node.
        parameters: Parameter bag for the node.
        children: Identifiers of child nodes.
    """
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: IRNodeType = IRNodeType.ACTION
    name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "parameters": dict(self.parameters),
            "children": list(self.children),
        }


@dataclass
class IREvent:
    """A named event composed of conditions and actions.

    Attributes:
        event_id: Unique identifier (auto-generated).
        name: Human-readable name of the event.
        conditions: Condition nodes that must all hold for the event to fire.
        actions: Action nodes executed when the event fires.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    conditions: List[IRNode] = field(default_factory=list)
    actions: List[IRNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class LogicIR:
    """A complete logic program composed of events and variables.

    Attributes:
        ir_id: Unique identifier (auto-generated).
        name: Human-readable name of the program.
        events: Events defined by the program.
        variables: Shared variable map for the program.
        version: Monotonically increasing version counter.
    """
    ir_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    events: List[IREvent] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ir_id": self.ir_id,
            "name": self.name,
            "events": [e.to_dict() for e in self.events],
            "variables": dict(self.variables),
            "version": self.version,
        }


@dataclass
class LogicIRSnapshot:
    """Immutable snapshot of the logic IR system state.

    Attributes:
        total_programs: Number of registered logic programs.
        total_events: Total number of events across all programs.
        total_nodes: Total number of IR nodes across all programs.
        programs: Serialized programs captured at snapshot time.
        timestamp: Time the snapshot was taken.
    """
    total_programs: int = 0
    total_events: int = 0
    total_nodes: int = 0
    programs: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_programs": self.total_programs,
            "total_events": self.total_events,
            "total_nodes": self.total_nodes,
            "programs": list(self.programs),
            "timestamp": self.timestamp,
        }


# =============================================================================
# Logic IR System (Singleton)
# =============================================================================


class LogicIRSystem:
    """Singleton logic IR system for LLM-friendly game logic authoring.

    Manages the creation, validation, serialization, and execution of
    logic programs expressed as data. All public methods are thread-safe.

    Typical usage::

        system = LogicIRSystem.get_instance()
        ir = system.create_ir("player_logic")
        event = IREvent(name="on_damage", conditions=[], actions=[])
        system.add_event(ir.ir_id, event)
        report = system.validate(ir.ir_id)
        result = system.execute(ir.ir_id, {"hp": 50})
    """

    _instance: Optional["LogicIRSystem"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "LogicIRSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._programs: Dict[str, LogicIR] = {}
        self._executions: int = 0
        self._validations: int = 0

    @classmethod
    def get_instance(cls) -> "LogicIRSystem":
        """Return the singleton LogicIRSystem instance (thread-safe)."""
        return cls()

    # ------------------------------------------------------------------
    # Program Management
    # ------------------------------------------------------------------

    def create_ir(self, name: str) -> LogicIR:
        """Create and register a new logic program.

        Args:
            name: Human-readable name of the program.

        Returns:
            The newly created LogicIR.
        """
        with self._instance_lock:
            ir = LogicIR(name=name)
            self._programs[ir.ir_id] = ir
            return ir

    def add_event(self, ir_id: str, event: IREvent) -> IREvent:
        """Attach an event to an existing logic program.

        Args:
            ir_id: Identifier of the target program.
            event: The event to attach.

        Returns:
            The attached event.

        Raises:
            KeyError: If the program id is not registered.
        """
        with self._instance_lock:
            ir = self._programs.get(ir_id)
            if ir is None:
                raise KeyError(f"Unknown logic IR: {ir_id}")
            ir.events.append(event)
            ir.version += 1
            return event

    def get_ir(self, ir_id: str) -> Optional[LogicIR]:
        """Return the logic program with the given id, if registered."""
        with self._instance_lock:
            return self._programs.get(ir_id)

    def get_all_ir(self) -> List[LogicIR]:
        """Return a copy of all registered logic programs."""
        with self._instance_lock:
            return list(self._programs.values())

    # ------------------------------------------------------------------
    # Validation and Execution
    # ------------------------------------------------------------------

    def validate(self, ir_id: str) -> Dict[str, Any]:
        """Validate a logic program and return a structured report.

        Args:
            ir_id: Identifier of the program to validate.

        Returns:
            A dict describing validity, errors, and warnings.
        """
        with self._instance_lock:
            self._validations += 1
            ir = self._programs.get(ir_id)
            if ir is None:
                return {
                    "ir_id": ir_id,
                    "valid": False,
                    "errors": [f"Unknown logic IR: {ir_id}"],
                    "warnings": [],
                }

            errors: List[str] = []
            warnings: List[str] = []
            seen_event_names = set()
            seen_node_ids = set()

            for event in ir.events:
                if not event.name:
                    errors.append("Event without a name detected")
                elif event.name in seen_event_names:
                    warnings.append(
                        f"Duplicate event name: {event.name}"
                    )
                else:
                    seen_event_names.add(event.name)

                for condition in event.conditions:
                    if condition.node_type != IRNodeType.CONDITION:
                        errors.append(
                            f"Condition node '{condition.name}' is not a CONDITION type"
                        )
                    if condition.node_id in seen_node_ids:
                        errors.append(f"Duplicate node id: {condition.node_id}")
                    else:
                        seen_node_ids.add(condition.node_id)

                # Executable node types allowed in the actions list. CONDITION
                # nodes belong in the conditions list; EVENT and VARIABLE are
                # structural and are not directly executable actions.
                executable_action_types = {
                    IRNodeType.ACTION,
                    IRNodeType.ASSIGN,
                    IRNodeType.BRANCH,
                    IRNodeType.LOOP,
                    IRNodeType.FUNCTION,
                }
                for action in event.actions:
                    if action.node_type not in executable_action_types:
                        errors.append(
                            f"Action node '{action.name}' has non-executable type {action.node_type.value}"
                        )
                    if action.node_id in seen_node_ids:
                        errors.append(f"Duplicate node id: {action.node_id}")
                    else:
                        seen_node_ids.add(action.node_id)

            return {
                "ir_id": ir_id,
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "event_count": len(ir.events),
                "node_count": len(seen_node_ids),
            }

    def execute(self, ir_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a logic program against a runtime context.

        Execution is a best-effort, side-effect-light pass: each event's
        action nodes are visited in order. Condition nodes that have a
        truthy ``parameters["value"]`` gate the action list. Variables are
        resolved against the supplied context, falling back to the program's
        shared variable map.

        Args:
            ir_id: Identifier of the program to execute.
            context: Runtime context merged on top of the program variables.

        Returns:
            A dict describing the execution outcome.
        """
        with self._instance_lock:
            self._executions += 1
            ir = self._programs.get(ir_id)
            if ir is None:
                return {
                    "ir_id": ir_id,
                    "success": False,
                    "error": f"Unknown logic IR: {ir_id}",
                    "events_fired": 0,
                    "actions_executed": 0,
                }

            runtime_vars = dict(ir.variables)
            if context:
                runtime_vars.update(context)

            events_fired = 0
            actions_executed = 0

            for event in ir.events:
                conditions_hold = True
                for condition in event.conditions:
                    value = condition.parameters.get("value", True)
                    if not value:
                        conditions_hold = False
                        break
                if not conditions_hold:
                    continue
                events_fired += 1
                for action in event.actions:
                    # Resolve simple assignment actions on the runtime vars.
                    if action.node_type == IRNodeType.ASSIGN:
                        target = action.parameters.get("target")
                        value = action.parameters.get("value")
                        if target is not None:
                            runtime_vars[str(target)] = value
                    actions_executed += 1

            # Propagate mutated variables back to the program.
            ir.variables = runtime_vars

            return {
                "ir_id": ir_id,
                "success": True,
                "events_fired": events_fired,
                "actions_executed": actions_executed,
                "variables": dict(runtime_vars),
            }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self, ir_id: str) -> str:
        """Serialize a logic program to a JSON string.

        Args:
            ir_id: Identifier of the program to serialize.

        Returns:
            A JSON string representation of the program.

        Raises:
            KeyError: If the program id is not registered.
        """
        with self._instance_lock:
            ir = self._programs.get(ir_id)
            if ir is None:
                raise KeyError(f"Unknown logic IR: {ir_id}")
            return json.dumps(ir.to_dict())

    def deserialize(self, json_str: str) -> LogicIR:
        """Reconstruct a logic program from a JSON string and register it.

        Args:
            json_str: JSON string previously produced by :meth:`serialize`.

        Returns:
            The reconstructed LogicIR, registered with the system.
        """
        with self._instance_lock:
            data = json.loads(json_str)
            ir = LogicIR(
                ir_id=data.get("ir_id") or uuid.uuid4().hex,
                name=data.get("name", ""),
                events=[
                    IREvent(
                        event_id=e.get("event_id") or uuid.uuid4().hex,
                        name=e.get("name", ""),
                        conditions=[
                            IRNode(
                                node_id=c.get("node_id") or uuid.uuid4().hex,
                                node_type=IRNodeType(c.get("node_type", IRNodeType.ACTION.value)),
                                name=c.get("name", ""),
                                parameters=dict(c.get("parameters", {})),
                                children=list(c.get("children", [])),
                            )
                            for c in e.get("conditions", [])
                        ],
                        actions=[
                            IRNode(
                                node_id=a.get("node_id") or uuid.uuid4().hex,
                                node_type=IRNodeType(a.get("node_type", IRNodeType.ACTION.value)),
                                name=a.get("name", ""),
                                parameters=dict(a.get("parameters", {})),
                                children=list(a.get("children", [])),
                            )
                            for a in e.get("actions", [])
                        ],
                    )
                    for e in data.get("events", [])
                ],
                variables=dict(data.get("variables", {})),
                version=int(data.get("version", 1)),
            )
            self._programs[ir.ir_id] = ir
            return ir

    # ------------------------------------------------------------------
    # Status and Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._instance_lock:
            total_events = sum(len(ir.events) for ir in self._programs.values())
            total_nodes = 0
            for ir in self._programs.values():
                for event in ir.events:
                    total_nodes += len(event.conditions) + len(event.actions)
            return {
                "total_programs": len(self._programs),
                "total_events": total_events,
                "total_nodes": total_nodes,
                "total_executions": self._executions,
                "total_validations": self._validations,
            }

    def get_snapshot(self) -> LogicIRSnapshot:
        """Capture an immutable snapshot of the system state."""
        with self._instance_lock:
            total_events = 0
            total_nodes = 0
            for ir in self._programs.values():
                total_events += len(ir.events)
                for event in ir.events:
                    total_nodes += len(event.conditions) + len(event.actions)
            return LogicIRSnapshot(
                total_programs=len(self._programs),
                total_events=total_events,
                total_nodes=total_nodes,
                programs=[ir.to_dict() for ir in self._programs.values()],
                timestamp=time.time(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all programs, executions, and counters."""
        with self._instance_lock:
            self._programs.clear()
            self._executions = 0
            self._validations = 0


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_logic_ir_system() -> LogicIRSystem:
    """Return the singleton LogicIRSystem instance."""
    return LogicIRSystem.get_instance()
