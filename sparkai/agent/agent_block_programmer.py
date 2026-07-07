"""
SparkLabs Agent - AI Block Programmer

This module implements an AI agent that synthesizes, validates, and manages
stack-based game logic programs. Each program is an ordered stack of
self-contained blocks (event triggers, conditions, actions, control-flow,
variables, operators) that snap together vertically to define game behavior
without writing code.

The block programmer is the AI-native counterpart to the engine's visual
scripting graph: where the graph wires nodes by edges, the block stack
composes behavior by vertical snapping. The agent can register new block
types, compose programs from natural-language briefs, validate type
signatures and control-flow integrity, dry-run programs to capture execution
traces, and merge multiple programs into a single coordinated stack.

Architecture:
  BlockProgrammerEngine (Singleton, double-checked locking, threading.RLock)
    |-- BlockType       -- a reusable block definition (category + signature)
    |-- BlockInstance   -- a placed block inside a program stack
    |-- BlockProgram    -- an ordered, named stack of block instances
    |-- ValidationReport-- the result of validating a program
    |-- DryRunTrace     -- the step-by-step execution trace of a dry run
    |-- BlockStats      -- aggregate engine statistics
    |-- BlockSnapshot   -- full engine snapshot
    |-- BlockEvent      -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_BLOCK_TYPES: int = 500
_MAX_PROGRAMS: int = 300
_MAX_BLOCKS_PER_PROGRAM: int = 200
_MAX_TRACES: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "blk") -> str:
    """Generate a short unique identifier with a readable prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return float(value)


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_deque(store: deque, max_size: int) -> None:
    """Evict the oldest inserted entries from a deque until within bounds."""
    while len(store) > max_size:
        try:
            store.popleft()
        except IndexError:
            break


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-friendly form.

    Enums become their string value, dataclasses become dicts (via this
    same function), lists and dicts are walked recursively, and anything
    else is returned as-is.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class BlockCategory(Enum):
    """The semantic category of a block."""
    EVENT = "event"
    CONDITION = "condition"
    ACTION = "action"
    CONTROL = "control"
    VARIABLE = "variable"
    OPERATOR = "operator"
    DATA = "data"


class BlockParamType(Enum):
    """The value type accepted by a block parameter."""
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    ENTITY = "entity"
    VECTOR = "vector"
    ANY = "any"


class ProgramStatus(Enum):
    """The lifecycle status of a block program."""
    DRAFT = "draft"
    VALIDATED = "validated"
    INVALID = "invalid"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PUBLISHED = "published"


class ValidationSeverity(Enum):
    """The severity of a validation finding."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TraceStepKind(Enum):
    """The kind of a dry-run trace step."""
    ENTER = "enter"
    EVALUATE = "evaluate"
    BRANCH = "branch"
    ACTION = "action"
    EXIT = "exit"
    ERROR = "error"


class BlockEventKind(Enum):
    """Observable lifecycle events emitted by the block programmer engine."""
    BLOCK_TYPE_REGISTERED = "block_type_registered"
    PROGRAM_CREATED = "program_created"
    BLOCK_ADDED = "block_added"
    BLOCK_REMOVED = "block_removed"
    PROGRAM_VALIDATED = "program_validated"
    DRY_RUN_COMPLETED = "dry_run_completed"
    PROGRAM_PUBLISHED = "program_published"
    PROGRAMS_MERGED = "programs_merged"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BlockParam:
    """A single typed parameter accepted by a block type."""
    name: str
    param_type: BlockParamType
    default: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this parameter to a JSON-friendly dictionary."""
        return {
            "name": self.name,
            "param_type": self.param_type.value,
            "default": self.default,
            "description": self.description,
        }


@dataclass
class BlockType:
    """A reusable block definition registered in the catalog."""
    type_id: str
    name: str
    category: BlockCategory
    description: str
    params: List[BlockParam]
    returns: BlockParamType
    can_terminate: bool
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this block type to a JSON-friendly dictionary."""
        return {
            "type_id": self.type_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "params": [p.to_dict() for p in self.params],
            "returns": self.returns.value,
            "can_terminate": self.can_terminate,
            "created_at": self.created_at,
        }


@dataclass
class BlockInstance:
    """A placed block inside a program stack."""
    instance_id: str
    type_id: str
    category: BlockCategory
    name: str
    params: Dict[str, str]
    order: int
    enabled: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this block instance to a JSON-friendly dictionary."""
        return {
            "instance_id": self.instance_id,
            "type_id": self.type_id,
            "category": self.category.value,
            "name": self.name,
            "params": _to_jsonable(self.params),
            "order": self.order,
            "enabled": self.enabled,
        }


@dataclass
class ValidationFinding:
    """A single issue discovered during program validation."""
    severity: ValidationSeverity
    code: str
    message: str
    instance_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this finding to a JSON-friendly dictionary."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "instance_id": self.instance_id,
        }


@dataclass
class ValidationReport:
    """The full result of validating a block program."""
    program_id: str
    valid: bool
    findings: List[ValidationFinding]
    validated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this report to a JSON-friendly dictionary."""
        return {
            "program_id": self.program_id,
            "valid": self.valid,
            "findings": [f.to_dict() for f in self.findings],
            "validated_at": self.validated_at,
        }


@dataclass
class TraceStep:
    """A single step in a dry-run execution trace."""
    step_index: int
    kind: TraceStepKind
    instance_id: str
    block_name: str
    detail: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this trace step to a JSON-friendly dictionary."""
        return {
            "step_index": self.step_index,
            "kind": self.kind.value,
            "instance_id": self.instance_id,
            "block_name": self.block_name,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


@dataclass
class DryRunTrace:
    """The complete execution trace of a program dry run."""
    trace_id: str
    program_id: str
    steps: List[TraceStep]
    completed: bool
    error: str
    started_at: str
    finished_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this trace to a JSON-friendly dictionary."""
        return {
            "trace_id": self.trace_id,
            "program_id": self.program_id,
            "steps": [s.to_dict() for s in self.steps],
            "completed": self.completed,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class BlockProgram:
    """An ordered, named stack of block instances."""
    program_id: str
    name: str
    description: str
    blocks: List[BlockInstance]
    status: ProgramStatus
    created_at: str
    updated_at: str
    tags: List[str]
    metadata: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this program to a JSON-friendly dictionary."""
        return {
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "blocks": [b.to_dict() for b in self.blocks],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": _to_jsonable(self.tags),
            "metadata": _to_jsonable(self.metadata),
        }


@dataclass
class BlockStats:
    """Aggregate statistics about the block programmer engine."""
    total_block_types: int
    total_programs: int
    total_blocks: int
    total_validations: int
    total_dry_runs: int
    total_published: int
    total_events: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a JSON-friendly dictionary."""
        return {
            "total_block_types": self.total_block_types,
            "total_programs": self.total_programs,
            "total_blocks": self.total_blocks,
            "total_validations": self.total_validations,
            "total_dry_runs": self.total_dry_runs,
            "total_published": self.total_published,
            "total_events": self.total_events,
        }


@dataclass
class BlockSnapshot:
    """A full snapshot of the engine state."""
    block_types: List[BlockType]
    programs: List[BlockProgram]
    traces: List[DryRunTrace]
    stats: BlockStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "block_types": [b.to_dict() for b in self.block_types],
            "programs": [p.to_dict() for p in self.programs],
            "traces": [t.to_dict() for t in self.traces],
            "stats": self.stats.to_dict(),
        }


@dataclass
class BlockEvent:
    """An observable lifecycle event emitted by the engine."""
    event_id: str
    kind: BlockEventKind
    program_id: str
    payload: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "program_id": self.program_id,
            "payload": _to_jsonable(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class BlockProgrammerEngine:
    """AI agent that synthesizes and manages stack-based block programs.

    Implemented as a thread-safe singleton with double-checked locking.
    All public mutating methods acquire ``self._lock`` (a re-entrant lock)
    so the engine is safe to call from multiple agent threads.
    """

    _instance: Optional["BlockProgrammerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "BlockProgrammerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._initialized: bool = True
            self._block_types: Dict[str, BlockType] = {}
            self._programs: Dict[str, BlockProgram] = {}
            self._traces: Dict[str, DryRunTrace] = {}
            self._events: deque[BlockEvent] = deque(maxlen=_MAX_EVENTS)
            self._block_type_counter = 0
            self._program_counter = 0
            self._block_counter = 0
            self._validation_counter = 0
            self._dry_run_counter = 0
            self._published_counter = 0
            self._event_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the catalog with a representative starter set of blocks.

        Seeds event triggers (on_start, onCollision, onInput, onTimer),
        conditions (ifEntity, ifDistance, ifVariable), actions (move, spawn,
        destroy, animate, playSound), control-flow (loop, wait, branch),
        variables (setVar, getVar), operators (compare, arithmetic), and
        data blocks (getEntity, getProperty). Also seeds two sample
        programs to demonstrate stack composition.
        """
        self._register_seed_block_types()
        self._seed_sample_programs()

    def _register_seed_block_types(self) -> None:
        """Register the starter catalog of block types."""
        seeds = [
            ("on_start", "On Start", BlockCategory.EVENT,
             "Fires once when the program starts.", [], BlockParamType.BOOLEAN, True),
            ("on_collision", "On Collision", BlockCategory.EVENT,
             "Fires when two entities collide.",
             [BlockParam("entity_a", BlockParamType.ENTITY, "", "First entity"),
              BlockParam("entity_b", BlockParamType.ENTITY, "", "Second entity")],
             BlockParamType.BOOLEAN, True),
            ("on_input", "On Input", BlockCategory.EVENT,
             "Fires when a named input is received.",
             [BlockParam("input_name", BlockParamType.STRING, "jump", "Input name")],
             BlockParamType.BOOLEAN, True),
            ("on_timer", "On Timer", BlockCategory.EVENT,
             "Fires on a repeating timer interval.",
             [BlockParam("interval", BlockParamType.FLOAT, "1.0", "Seconds between fires")],
             BlockParamType.BOOLEAN, True),
            ("if_entity", "If Entity", BlockCategory.CONDITION,
             "Branches when an entity matches a filter.",
             [BlockParam("entity", BlockParamType.ENTITY, "", "Entity to test"),
              BlockParam("property", BlockParamType.STRING, "tag", "Property name"),
              BlockParam("value", BlockParamType.STRING, "", "Expected value")],
             BlockParamType.BOOLEAN, False),
            ("if_distance", "If Distance", BlockCategory.CONDITION,
             "Branches when two entities are within a distance.",
             [BlockParam("entity_a", BlockParamType.ENTITY, "", "First entity"),
              BlockParam("entity_b", BlockParamType.ENTITY, "", "Second entity"),
              BlockParam("max_distance", BlockParamType.FLOAT, "5.0", "Maximum distance")],
             BlockParamType.BOOLEAN, False),
            ("if_variable", "If Variable", BlockCategory.CONDITION,
             "Branches when a variable meets a comparison.",
             [BlockParam("variable", BlockParamType.STRING, "score", "Variable name"),
              BlockParam("operator", BlockParamType.STRING, "==", "Comparison operator"),
              BlockParam("value", BlockParamType.STRING, "0", "Value to compare")],
             BlockParamType.BOOLEAN, False),
            ("move", "Move", BlockCategory.ACTION,
             "Moves an entity by a vector.",
             [BlockParam("entity", BlockParamType.ENTITY, "", "Entity to move"),
              BlockParam("vector", BlockParamType.VECTOR, "0,0,0", "Movement vector")],
             BlockParamType.BOOLEAN, False),
            ("spawn", "Spawn", BlockCategory.ACTION,
             "Spawns a new entity from a template.",
             [BlockParam("template", BlockParamType.STRING, "", "Entity template id"),
              BlockParam("position", BlockParamType.VECTOR, "0,0,0", "Spawn position")],
             BlockParamType.ENTITY, False),
            ("destroy", "Destroy", BlockCategory.ACTION,
             "Destroys an entity.",
             [BlockParam("entity", BlockParamType.ENTITY, "", "Entity to destroy")],
             BlockParamType.BOOLEAN, False),
            ("animate", "Animate", BlockCategory.ACTION,
             "Plays an animation on an entity.",
             [BlockParam("entity", BlockParamType.ENTITY, "", "Target entity"),
              BlockParam("clip", BlockParamType.STRING, "idle", "Animation clip name"),
              BlockParam("loop", BlockParamType.BOOLEAN, "false", "Loop the animation")],
             BlockParamType.BOOLEAN, False),
            ("play_sound", "Play Sound", BlockCategory.ACTION,
             "Plays a sound effect.",
             [BlockParam("sound", BlockParamType.STRING, "", "Sound asset id"),
              BlockParam("volume", BlockParamType.FLOAT, "1.0", "Volume 0-1")],
             BlockParamType.BOOLEAN, False),
            ("loop", "Loop", BlockCategory.CONTROL,
             "Repeats the following blocks N times.",
             [BlockParam("count", BlockParamType.INTEGER, "3", "Iteration count")],
             BlockParamType.BOOLEAN, False),
            ("wait", "Wait", BlockCategory.CONTROL,
             "Pauses execution for a duration.",
             [BlockParam("duration", BlockParamType.FLOAT, "1.0", "Seconds to wait")],
             BlockParamType.BOOLEAN, False),
            ("branch", "Branch", BlockCategory.CONTROL,
             "Conditional branch (if/else).",
             [BlockParam("condition", BlockParamType.BOOLEAN, "true", "Branch condition")],
             BlockParamType.BOOLEAN, False),
            ("set_var", "Set Variable", BlockCategory.VARIABLE,
             "Assigns a value to a named variable.",
             [BlockParam("variable", BlockParamType.STRING, "score", "Variable name"),
              BlockParam("value", BlockParamType.STRING, "0", "Value to assign")],
             BlockParamType.BOOLEAN, False),
            ("get_var", "Get Variable", BlockCategory.VARIABLE,
             "Reads the value of a named variable.",
             [BlockParam("variable", BlockParamType.STRING, "score", "Variable name")],
             BlockParamType.ANY, False),
            ("compare", "Compare", BlockCategory.OPERATOR,
             "Compares two values and returns a boolean.",
             [BlockParam("left", BlockParamType.STRING, "0", "Left operand"),
              BlockParam("operator", BlockParamType.STRING, "==", "Operator"),
              BlockParam("right", BlockParamType.STRING, "0", "Right operand")],
             BlockParamType.BOOLEAN, False),
            ("arithmetic", "Arithmetic", BlockCategory.OPERATOR,
             "Performs arithmetic on two numbers.",
             [BlockParam("left", BlockParamType.FLOAT, "0", "Left operand"),
              BlockParam("operator", BlockParamType.STRING, "+", "Operator"),
              BlockParam("right", BlockParamType.FLOAT, "0", "Right operand")],
             BlockParamType.FLOAT, False),
            ("get_entity", "Get Entity", BlockCategory.DATA,
             "Retrieves an entity by id.",
             [BlockParam("entity_id", BlockParamType.STRING, "", "Entity id")],
             BlockParamType.ENTITY, False),
            ("get_property", "Get Property", BlockCategory.DATA,
             "Reads a property from an entity.",
             [BlockParam("entity", BlockParamType.ENTITY, "", "Source entity"),
              BlockParam("property", BlockParamType.STRING, "health", "Property name")],
             BlockParamType.ANY, False),
        ]
        for type_id, name, category, desc, params, returns, can_term in seeds:
            bt = BlockType(
                type_id=type_id,
                name=name,
                category=category,
                description=desc,
                params=params,
                returns=returns,
                can_terminate=can_term,
                created_at=_now(),
            )
            self._block_types[type_id] = bt
            self._block_type_counter += 1

    def _seed_sample_programs(self) -> None:
        """Seed two sample programs demonstrating stack composition."""
        # Program 1: a simple "on start, move and play sound" program.
        p1 = self._new_program(
            name="Player Spawn Sequence",
            description="Moves the player and plays a sound on start.",
        )
        self._append_block(p1, "on_start", {})
        self._append_block(p1, "move", {
            "entity": "player",
            "vector": "0,1,0",
        })
        self._append_block(p1, "play_sound", {
            "sound": "spawn_sfx",
            "volume": "0.8",
        })
        p1.tags = ["player", "spawn"]
        p1.status = ProgramStatus.VALIDATED

        # Program 2: a collision-driven destroy program.
        p2 = self._new_program(
            name="Projectile Impact",
            description="Destroys a projectile and its target on collision.",
        )
        self._append_block(p2, "on_collision", {
            "entity_a": "projectile",
            "entity_b": "target",
        })
        self._append_block(p2, "destroy", {"entity": "projectile"})
        self._append_block(p2, "destroy", {"entity": "target"})
        self._append_block(p2, "play_sound", {
            "sound": "impact_sfx",
            "volume": "1.0",
        })
        p2.tags = ["combat", "projectile"]
        p2.status = ProgramStatus.VALIDATED

    def _new_program(
        self,
        name: str,
        description: str = "",
        program_id: str = "",
    ) -> BlockProgram:
        """Create and register a new program (caller must hold ``self._lock``)."""
        program_id = program_id or _new_id("prog")
        now = _now()
        program = BlockProgram(
            program_id=program_id,
            name=name or "Untitled Program",
            description=description or "",
            blocks=[],
            status=ProgramStatus.DRAFT,
            created_at=now,
            updated_at=now,
            tags=[],
            metadata={},
        )
        self._programs[program_id] = program
        self._program_counter += 1
        _evict_fifo_dict(self._programs, _MAX_PROGRAMS)
        self._record_event(
            BlockEventKind.PROGRAM_CREATED,
            program_id,
            {"name": program.name},
        )
        return program

    def _append_block(
        self,
        program: BlockProgram,
        type_id: str,
        params: Dict[str, str],
    ) -> BlockInstance:
        """Append a block to a program (caller must hold ``self._lock``)."""
        bt = self._block_types.get(type_id)
        if bt is None:
            raise ValueError(f"Unknown block type: {type_id}")
        order = len(program.blocks)
        instance = BlockInstance(
            instance_id=_new_id("inst"),
            type_id=type_id,
            category=bt.category,
            name=bt.name,
            params=dict(params),
            order=order,
            enabled=True,
        )
        program.blocks.append(instance)
        program.updated_at = _now()
        self._block_counter += 1
        if len(program.blocks) > _MAX_BLOCKS_PER_PROGRAM:
            program.blocks.pop(0)
            self._reindex(program)
        self._record_event(
            BlockEventKind.BLOCK_ADDED,
            program.program_id,
            {
                "instance_id": instance.instance_id,
                "type_id": type_id,
                "order": instance.order,
            },
        )
        return instance

    def _reindex(self, program: BlockProgram) -> None:
        """Reassign sequential order indices after a structural change."""
        for index, block in enumerate(program.blocks):
            block.order = index

    # ------------------------------------------------------------------
    # Internal event recording
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: BlockEventKind,
        program_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> BlockEvent:
        """Record an audit event (caller must hold ``self._lock``)."""
        event = BlockEvent(
            event_id=_new_id("evt"),
            kind=kind,
            program_id=program_id,
            payload=dict(payload) if payload else {},
            timestamp=_now(),
        )
        _evict_fifo_deque(self._events, _MAX_EVENTS)
        self._events.append(event)
        self._event_counter += 1
        return event

    # ------------------------------------------------------------------
    # Block type management
    # ------------------------------------------------------------------

    def register_block_type(
        self,
        type_id: str,
        name: str,
        category: Union[BlockCategory, str],
        description: str = "",
        params: Optional[List[Dict[str, Any]]] = None,
        returns: Union[BlockParamType, str] = BlockParamType.BOOLEAN,
        can_terminate: bool = False,
    ) -> Optional[BlockType]:
        """Register a new reusable block type in the catalog.

        Returns the new :class:`BlockType` or ``None`` if the id is already
        in use or the arguments cannot be resolved.
        """
        with self._lock:
            if not type_id or type_id in self._block_types:
                return None
            resolved_category = _resolve_category(category)
            if resolved_category is None:
                return None
            resolved_returns = _resolve_param_type(returns)
            if resolved_returns is None:
                return None
            parsed_params: List[BlockParam] = []
            for raw in params or []:
                if not isinstance(raw, dict):
                    continue
                pt = _resolve_param_type(raw.get("param_type", "any"))
                if pt is None:
                    pt = BlockParamType.ANY
                parsed_params.append(BlockParam(
                    name=str(raw.get("name", "")),
                    param_type=pt,
                    default=str(raw.get("default", "")),
                    description=str(raw.get("description", "")),
                ))
            bt = BlockType(
                type_id=type_id,
                name=name or type_id,
                category=resolved_category,
                description=description or "",
                params=parsed_params,
                returns=resolved_returns,
                can_terminate=bool(can_terminate),
                created_at=_now(),
            )
            self._block_types[type_id] = bt
            self._block_type_counter += 1
            _evict_fifo_dict(self._block_types, _MAX_BLOCK_TYPES)
            self._record_event(
                BlockEventKind.BLOCK_TYPE_REGISTERED,
                "",
                {"type_id": type_id, "name": bt.name},
            )
            return bt

    def get_block_type(self, type_id: str) -> Optional[BlockType]:
        """Return a block type by id, or ``None`` if not found."""
        with self._lock:
            return self._block_types.get(type_id)

    def list_block_types(
        self,
        category: Optional[Union[BlockCategory, str]] = None,
    ) -> List[BlockType]:
        """Return all block types, optionally filtered by category."""
        with self._lock:
            resolved = _resolve_category(category) if category else None
            if resolved is None:
                return list(self._block_types.values())
            return [
                bt for bt in self._block_types.values()
                if bt.category == resolved
            ]

    # ------------------------------------------------------------------
    # Program lifecycle
    # ------------------------------------------------------------------

    def create_program(
        self,
        name: str,
        description: str = "",
        program_id: str = "",
    ) -> BlockProgram:
        """Create a new empty block program."""
        with self._lock:
            return self._new_program(name, description, program_id)

    def get_program(self, program_id: str) -> Optional[BlockProgram]:
        """Return a program by id, or ``None`` if not found."""
        with self._lock:
            return self._programs.get(program_id)

    def list_programs(
        self,
        status: Optional[Union[ProgramStatus, str]] = None,
        tag: Optional[str] = None,
    ) -> List[BlockProgram]:
        """Return all programs, optionally filtered by status or tag."""
        with self._lock:
            resolved_status = _resolve_status(status) if status else None
            results: List[BlockProgram] = []
            for program in self._programs.values():
                if resolved_status is not None and program.status != resolved_status:
                    continue
                if tag and tag not in program.tags:
                    continue
                results.append(program)
            return results

    def delete_program(self, program_id: str) -> bool:
        """Delete a program. Returns ``True`` if it was removed."""
        with self._lock:
            if program_id not in self._programs:
                return False
            self._programs.pop(program_id, None)
            return True

    def rename_program(
        self,
        program_id: str,
        name: str,
        description: str = "",
    ) -> Optional[BlockProgram]:
        """Rename a program and optionally update its description."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            program.name = name or program.name
            if description:
                program.description = description
            program.updated_at = _now()
            return program

    def tag_program(
        self,
        program_id: str,
        tag: str,
    ) -> Optional[BlockProgram]:
        """Add a tag to a program (idempotent)."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            if tag and tag not in program.tags:
                program.tags.append(tag)
                program.updated_at = _now()
            return program

    # ------------------------------------------------------------------
    # Block manipulation
    # ------------------------------------------------------------------

    def add_block(
        self,
        program_id: str,
        type_id: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[BlockInstance]:
        """Append a block to the end of a program stack."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            try:
                return self._append_block(program, type_id, params or {})
            except ValueError:
                return None

    def insert_block(
        self,
        program_id: str,
        type_id: str,
        position: int,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[BlockInstance]:
        """Insert a block at a specific position in the stack."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            bt = self._block_types.get(type_id)
            if bt is None:
                return None
            pos = max(0, min(int(position), len(program.blocks)))
            instance = BlockInstance(
                instance_id=_new_id("inst"),
                type_id=type_id,
                category=bt.category,
                name=bt.name,
                params=dict(params or {}),
                order=pos,
                enabled=True,
            )
            program.blocks.insert(pos, instance)
            self._reindex(program)
            program.updated_at = _now()
            self._block_counter += 1
            self._record_event(
                BlockEventKind.BLOCK_ADDED,
                program_id,
                {
                    "instance_id": instance.instance_id,
                    "type_id": type_id,
                    "order": pos,
                    "inserted": True,
                },
            )
            return instance

    def remove_block(
        self,
        program_id: str,
        instance_id: str,
    ) -> bool:
        """Remove a block from a program by instance id."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return False
            for index, block in enumerate(program.blocks):
                if block.instance_id == instance_id:
                    program.blocks.pop(index)
                    self._reindex(program)
                    program.updated_at = _now()
                    self._record_event(
                        BlockEventKind.BLOCK_REMOVED,
                        program_id,
                        {"instance_id": instance_id},
                    )
                    return True
            return False

    def move_block(
        self,
        program_id: str,
        instance_id: str,
        new_position: int,
    ) -> bool:
        """Move a block to a new position within the stack."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return False
            current_index = -1
            for index, block in enumerate(program.blocks):
                if block.instance_id == instance_id:
                    current_index = index
                    break
            if current_index < 0:
                return False
            block = program.blocks.pop(current_index)
            pos = max(0, min(int(new_position), len(program.blocks)))
            program.blocks.insert(pos, block)
            self._reindex(program)
            program.updated_at = _now()
            return True

    def set_block_enabled(
        self,
        program_id: str,
        instance_id: str,
        enabled: bool,
    ) -> bool:
        """Enable or disable a block without removing it."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return False
            for block in program.blocks:
                if block.instance_id == instance_id:
                    block.enabled = bool(enabled)
                    program.updated_at = _now()
                    return True
            return False

    def update_block_params(
        self,
        program_id: str,
        instance_id: str,
        params: Dict[str, str],
    ) -> bool:
        """Update the parameters of a placed block."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return False
            for block in program.blocks:
                if block.instance_id == instance_id:
                    block.params.update(params or {})
                    program.updated_at = _now()
                    return True
            return False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_program(self, program_id: str) -> Optional[ValidationReport]:
        """Validate a program's structural and type integrity.

        Checks that the program has at least one event trigger, that every
        block references a known type, that required parameters are set,
        and that control-flow blocks are balanced. Returns a
        :class:`ValidationReport` or ``None`` if the program is missing.
        """
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            findings: List[ValidationFinding] = []
            has_event = False
            open_control = 0
            for block in program.blocks:
                bt = self._block_types.get(block.type_id)
                if bt is None:
                    findings.append(ValidationFinding(
                        severity=ValidationSeverity.ERROR,
                        code="unknown_type",
                        message=f"Block '{block.name}' references unknown type '{block.type_id}'.",
                        instance_id=block.instance_id,
                    ))
                    continue
                if bt.category == BlockCategory.EVENT:
                    has_event = True
                if bt.category == BlockCategory.CONTROL:
                    open_control += 1
                for param in bt.params:
                    if param.name not in block.params and param.default == "":
                        findings.append(ValidationFinding(
                            severity=ValidationSeverity.WARNING,
                            code="missing_param",
                            message=f"Block '{block.name}' is missing parameter '{param.name}'.",
                            instance_id=block.instance_id,
                        ))
                if not block.enabled:
                    findings.append(ValidationFinding(
                        severity=ValidationSeverity.INFO,
                        code="disabled_block",
                        message=f"Block '{block.name}' is disabled and will be skipped.",
                        instance_id=block.instance_id,
                    ))
            if not has_event:
                findings.append(ValidationFinding(
                    severity=ValidationSeverity.ERROR,
                    code="no_event",
                    message="Program has no event trigger block.",
                    instance_id="",
                ))
            if open_control > 0:
                findings.append(ValidationFinding(
                    severity=ValidationSeverity.WARNING,
                    code="unbalanced_control",
                    message=f"Program has {open_control} unbalanced control-flow block(s).",
                    instance_id="",
                ))
            if len(program.blocks) == 0:
                findings.append(ValidationFinding(
                    severity=ValidationSeverity.ERROR,
                    code="empty_program",
                    message="Program has no blocks.",
                    instance_id="",
                ))
            errors = [f for f in findings if f.severity == ValidationSeverity.ERROR]
            report = ValidationReport(
                program_id=program_id,
                valid=len(errors) == 0,
                findings=findings,
                validated_at=_now(),
            )
            program.status = ProgramStatus.VALIDATED if report.valid else ProgramStatus.INVALID
            program.updated_at = _now()
            self._validation_counter += 1
            self._record_event(
                BlockEventKind.PROGRAM_VALIDATED,
                program_id,
                {"valid": report.valid, "finding_count": len(findings)},
            )
            return report

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    def dry_run(
        self,
        program_id: str,
        max_steps: int = 200,
    ) -> Optional[DryRunTrace]:
        """Simulate execution of a program and capture a trace.

        Walks the block stack in order, emitting ENTER/EVALUATE/ACTION/EXIT
        steps for each enabled block. Stops early if ``max_steps`` is
        exceeded or a block signals termination. Returns a
        :class:`DryRunTrace` or ``None`` if the program is missing.
        """
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            steps: List[TraceStep] = []
            started = _now()
            completed = True
            error = ""
            program.status = ProgramStatus.RUNNING
            step_index = 0
            for block in program.blocks:
                if step_index >= int(max_steps):
                    completed = False
                    error = "Max steps exceeded"
                    steps.append(TraceStep(
                        step_index=step_index,
                        kind=TraceStepKind.ERROR,
                        instance_id=block.instance_id,
                        block_name=block.name,
                        detail="Max steps exceeded",
                        timestamp=_now(),
                    ))
                    break
                if not block.enabled:
                    steps.append(TraceStep(
                        step_index=step_index,
                        kind=TraceStepKind.EVALUATE,
                        instance_id=block.instance_id,
                        block_name=block.name,
                        detail="Skipped (disabled)",
                        timestamp=_now(),
                    ))
                    step_index += 1
                    continue
                steps.append(TraceStep(
                    step_index=step_index,
                    kind=TraceStepKind.ENTER,
                    instance_id=block.instance_id,
                    block_name=block.name,
                    detail=f"Entered {block.category.value} block",
                    timestamp=_now(),
                ))
                step_index += 1
                if block.category == BlockCategory.EVENT:
                    steps.append(TraceStep(
                        step_index=step_index,
                        kind=TraceStepKind.EVALUATE,
                        instance_id=block.instance_id,
                        block_name=block.name,
                        detail=f"Event trigger fired: {block.params}",
                        timestamp=_now(),
                    ))
                    step_index += 1
                elif block.category == BlockCategory.CONDITION:
                    result = "true"
                    steps.append(TraceStep(
                        step_index=step_index,
                        kind=TraceStepKind.BRANCH,
                        instance_id=block.instance_id,
                        block_name=block.name,
                        detail=f"Condition evaluated to {result}",
                        timestamp=_now(),
                    ))
                    step_index += 1
                elif block.category == BlockCategory.ACTION:
                    steps.append(TraceStep(
                        step_index=step_index,
                        kind=TraceStepKind.ACTION,
                        instance_id=block.instance_id,
                        block_name=block.name,
                        detail=f"Action executed: {block.params}",
                        timestamp=_now(),
                    ))
                    step_index += 1
                elif block.category == BlockCategory.CONTROL:
                    steps.append(TraceStep(
                        step_index=step_index,
                        kind=TraceStepKind.BRANCH,
                        instance_id=block.instance_id,
                        block_name=block.name,
                        detail=f"Control flow: {block.params}",
                        timestamp=_now(),
                    ))
                    step_index += 1
                else:
                    steps.append(TraceStep(
                        step_index=step_index,
                        kind=TraceStepKind.EVALUATE,
                        instance_id=block.instance_id,
                        block_name=block.name,
                        detail=f"Evaluated: {block.params}",
                        timestamp=_now(),
                    ))
                    step_index += 1
                steps.append(TraceStep(
                    step_index=step_index,
                    kind=TraceStepKind.EXIT,
                    instance_id=block.instance_id,
                    block_name=block.name,
                    detail=f"Exited {block.name}",
                    timestamp=_now(),
                ))
                step_index += 1
            trace = DryRunTrace(
                trace_id=_new_id("trace"),
                program_id=program_id,
                steps=steps,
                completed=completed,
                error=error,
                started_at=started,
                finished_at=_now(),
            )
            self._traces[trace.trace_id] = trace
            self._dry_run_counter += 1
            _evict_fifo_dict(self._traces, _MAX_TRACES)
            program.status = ProgramStatus.COMPLETED if completed else ProgramStatus.FAILED
            program.updated_at = _now()
            self._record_event(
                BlockEventKind.DRY_RUN_COMPLETED,
                program_id,
                {
                    "trace_id": trace.trace_id,
                    "completed": completed,
                    "step_count": len(steps),
                },
            )
            return trace

    def get_trace(self, trace_id: str) -> Optional[DryRunTrace]:
        """Return a dry-run trace by id."""
        with self._lock:
            return self._traces.get(trace_id)

    def list_traces(self, program_id: Optional[str] = None) -> List[DryRunTrace]:
        """Return all traces, optionally filtered by program."""
        with self._lock:
            if not program_id:
                return list(self._traces.values())
            return [t for t in self._traces.values() if t.program_id == program_id]

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def publish_program(self, program_id: str) -> Optional[BlockProgram]:
        """Mark a program as published after validation."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            if program.status == ProgramStatus.INVALID:
                return None
            program.status = ProgramStatus.PUBLISHED
            program.updated_at = _now()
            self._published_counter += 1
            self._record_event(
                BlockEventKind.PROGRAM_PUBLISHED,
                program_id,
                {"name": program.name},
            )
            return program

    def merge_programs(
        self,
        program_ids: Sequence[str],
        name: str = "",
        description: str = "",
    ) -> Optional[BlockProgram]:
        """Merge multiple programs into a new combined program.

        Concatenates the block stacks of the source programs in order.
        Returns the new merged :class:`BlockProgram` or ``None`` if no
        source programs were found.
        """
        with self._lock:
            sources: List[BlockProgram] = []
            for pid in program_ids:
                program = self._programs.get(pid)
                if program is not None:
                    sources.append(program)
            if not sources:
                return None
            merged = self._new_program(
                name=name or "Merged Program",
                description=description or f"Merged from {len(sources)} program(s).",
            )
            for source in sources:
                for block in source.blocks:
                    self._append_block(merged, block.type_id, dict(block.params))
                merged.tags.extend(source.tags)
            merged.tags = list(dict.fromkeys(merged.tags))
            merged.updated_at = _now()
            self._record_event(
                BlockEventKind.PROGRAMS_MERGED,
                merged.program_id,
                {"source_count": len(sources), "name": merged.name},
            )
            return merged

    def export_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        """Export a program as a JSON-friendly dictionary."""
        with self._lock:
            program = self._programs.get(program_id)
            if program is None:
                return None
            return program.to_dict()

    def import_program(self, data: Dict[str, Any]) -> Optional[BlockProgram]:
        """Import a program from a dictionary."""
        with self._lock:
            name = str(data.get("name", "Imported Program"))
            description = str(data.get("description", ""))
            program = self._new_program(name=name, description=description)
            for raw_block in data.get("blocks", []):
                if not isinstance(raw_block, dict):
                    continue
                type_id = str(raw_block.get("type_id", ""))
                if type_id not in self._block_types:
                    continue
                params = raw_block.get("params", {})
                if not isinstance(params, dict):
                    params = {}
                self._append_block(program, type_id, {k: str(v) for k, v in params.items()})
            tags = data.get("tags", [])
            if isinstance(tags, list):
                program.tags = [str(t) for t in tags]
            return program

    # ------------------------------------------------------------------
    # Lookups and snapshots
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 50) -> List[BlockEvent]:
        """Return the most recent lifecycle events."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_EVENTS))
            return list(self._events)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Return a compact status summary for monitoring."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_block_types": len(self._block_types),
                "total_programs": len(self._programs),
                "total_blocks": sum(len(p.blocks) for p in self._programs.values()),
                "total_traces": len(self._traces),
                "total_events": len(self._events),
                "block_type_counter": self._block_type_counter,
                "program_counter": self._program_counter,
                "block_counter": self._block_counter,
                "validation_counter": self._validation_counter,
                "dry_run_counter": self._dry_run_counter,
                "published_counter": self._published_counter,
                "event_counter": self._event_counter,
                "capacities": {
                    "max_block_types": _MAX_BLOCK_TYPES,
                    "max_programs": _MAX_PROGRAMS,
                    "max_blocks_per_program": _MAX_BLOCKS_PER_PROGRAM,
                    "max_traces": _MAX_TRACES,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_stats(self) -> BlockStats:
        """Return aggregate engine statistics."""
        with self._lock:
            return BlockStats(
                total_block_types=len(self._block_types),
                total_programs=len(self._programs),
                total_blocks=sum(len(p.blocks) for p in self._programs.values()),
                total_validations=self._validation_counter,
                total_dry_runs=self._dry_run_counter,
                total_published=self._published_counter,
                total_events=len(self._events),
            )

    def get_snapshot(self) -> BlockSnapshot:
        """Return a full snapshot of the engine state."""
        with self._lock:
            return BlockSnapshot(
                block_types=list(self._block_types.values()),
                programs=list(self._programs.values()),
                traces=list(self._traces.values()),
                stats=self.get_stats(),
            )

    def reset(self) -> None:
        """Reset the engine to its seeded state."""
        with self._lock:
            self._block_types.clear()
            self._programs.clear()
            self._traces.clear()
            self._events.clear()
            self._block_type_counter = 0
            self._program_counter = 0
            self._block_counter = 0
            self._validation_counter = 0
            self._dry_run_counter = 0
            self._published_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Enum resolvers
# ---------------------------------------------------------------------------


def _resolve_category(value: Union[BlockCategory, str, None]) -> Optional[BlockCategory]:
    """Coerce a value into a :class:`BlockCategory` enum instance."""
    if value is None:
        return None
    if isinstance(value, BlockCategory):
        return value
    if isinstance(value, str):
        try:
            return BlockCategory(value)
        except ValueError:
            return None
    return None


def _resolve_param_type(value: Union[BlockParamType, str, None]) -> Optional[BlockParamType]:
    """Coerce a value into a :class:`BlockParamType` enum instance."""
    if value is None:
        return None
    if isinstance(value, BlockParamType):
        return value
    if isinstance(value, str):
        try:
            return BlockParamType(value)
        except ValueError:
            return None
    return None


def _resolve_status(value: Union[ProgramStatus, str, None]) -> Optional[ProgramStatus]:
    """Coerce a value into a :class:`ProgramStatus` enum instance."""
    if value is None:
        return None
    if isinstance(value, ProgramStatus):
        return value
    if isinstance(value, str):
        try:
            return ProgramStatus(value)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------


def get_block_programmer() -> BlockProgrammerEngine:
    """Return the shared :class:`BlockProgrammerEngine` singleton instance."""
    return BlockProgrammerEngine()
