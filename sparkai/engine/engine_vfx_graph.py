"""
SparkLabs Engine - VFX Graph System

A node-based composable visual effects (VFX) graph engine for the
SparkLabs AI-native game engine. VFX graphs are directed acyclic graphs
(DAGs) of nodes where each node represents an operation (emitter,
modifier, renderer, etc.) and the connections between nodes define the
data flow. This enables designers to compose complex visual effects by
connecting nodes together in a visual editor.

Architecture:
  VFXGraphEngine (singleton)
    |-- VFXPin             -- a connection point on a node (input/output/inout)
    |-- VFXNode            -- a single operation within a graph
    |-- VFXConnection      -- a typed edge linking two pins
    |-- VFXParameter       -- an exposed, tunable graph parameter
    |-- VFXGraph           -- a complete DAG of nodes and connections
    |-- VFXGraphInstance   -- a runtime instantiation of a compiled graph
    |-- VFXCompileResult   -- the outcome of validating/compiling a graph
    |-- VFXGraphStats      -- aggregate counters describing the engine state
    |-- VFXGraphSnapshot   -- immutable snapshot of the whole engine
    |-- VFXGraphEvent      -- audit log entry for lifecycle changes
    |-- VFXNodeType        -- 15 node operation classifications
    |-- VFXPinKind         -- input / output / inout
    |-- VFXDataType        -- 8 pin data classifications
    |-- GraphStatus        -- draft / compiled / active / error
    |-- RenderSpace        -- world / local / screen
    |-- BlendMode          -- additive / alpha / multiplicative / subtractive
    |-- SortingMode        -- by distance / age / index / unsorted
    |-- VFXEventKind       -- 10 audit event kinds

Core Capabilities:
  - create_graph / list_graphs / get_graph / update_graph / delete_graph:
    graph registry management with FIFO eviction.
  - add_node / get_node / list_nodes / update_node / remove_node: node
    management with automatic default-pin creation based on node type.
  - connect / disconnect / list_connections: typed pin connections with
    cycle detection and data-type compatibility validation.
  - add_parameter / set_parameter / list_parameters: exposed graph
    parameters with min/max clamping.
  - compile_graph: validate the graph (cycles, type mismatches,
    unconnected pins) and set the status to COMPILED or ERROR.
  - instantiate_graph / get_instance / list_instances / stop_instance:
    runtime instance management for compiled graphs.
  - list_events / get_stats / get_status / get_snapshot: observability.
  - reset: clear all stores and re-seed with default data.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`VFXGraphEngine.get_instance` or the module-level
:func:`get_vfx_graph` factory. All public methods are guarded by the
re-entrant lock.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under heavy
# dynamic use (for example a game that creates a new graph for every
# spell cast or ability trigger).
_MAX_GRAPHS: int = 500
_MAX_INSTANCES: int = 2000
_MAX_COMPILE_RESULTS: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for ``created_at`` / ``updated_at``
    fields and for event timestamps throughout the module.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with
            an underscore. When omitted, the bare hexadecimal id is
            returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive ``[low, high]`` range.

    Args:
        value: The value to clamp.
        low: The inclusive lower bound.
        high: The inclusive upper bound.

    Returns:
        The clamped value.
    """
    if value < low:
        return low
    if value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class VFXNodeType(Enum):
    """Classification of a VFX node operation.

    Each node type determines the default pins that are created when a
    node is added to a graph. Particle-modifier nodes (FORCE_FIELD,
    COLOR_GRADIENT, etc.) share a common in/out PARTICLE_STREAM pattern
    so they can be chained together in sequence.
    """

    EMITTER = "emitter"
    PARTICLE_INIT = "particle_init"
    FORCE_FIELD = "force_field"
    COLLIDER = "collider"
    COLOR_GRADIENT = "color_gradient"
    SIZE_CURVE = "size_curve"
    ROTATION_MOD = "rotation_mod"
    VELOCITY_MOD = "velocity_mod"
    LIFETIME_MOD = "lifetime_mod"
    TRAIL = "trail"
    NOISE_FIELD = "noise_field"
    RENDERER = "renderer"
    SUBGRAPH = "subgraph"
    MATH_OP = "math_op"
    PARAMETER = "parameter"


class VFXPinKind(Enum):
    """The directional role of a pin on a node.

    - ``INPUT``: accepts incoming data from exactly one source pin.
    - ``OUTPUT``: produces data that may feed one or more input pins.
    - ``INOUT``: can act as either input or output (rare; used by some
      sub-graph and pass-through nodes).
    """

    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"


class VFXDataType(Enum):
    """The data classification carried by a pin or connection.

    - ``PARTICLE_STREAM``: a live stream of particle data.
    - ``FLOAT``: a single-precision scalar.
    - ``VECTOR3``: a three-component vector.
    - ``COLOR``: an RGBA color.
    - ``CURVE``: an animation curve over time.
    - ``GRADIENT``: a color gradient over time.
    - ``TEXTURE``: a texture reference.
    - ``BOOL``: a boolean flag.
    - ``INT``: an integer scalar.
    """

    PARTICLE_STREAM = "particle_stream"
    FLOAT = "float"
    VECTOR3 = "vector3"
    COLOR = "color"
    CURVE = "curve"
    GRADIENT = "gradient"
    TEXTURE = "texture"
    BOOL = "bool"
    INT = "int"


class GraphStatus(Enum):
    """Lifecycle status of a VFX graph.

    - ``DRAFT``: newly created or edited; not yet validated.
    - ``COMPILED``: passed validation and ready for instantiation.
    - ``ACTIVE``: has at least one running instance.
    - ``ERROR``: failed validation and cannot be instantiated.
    """

    DRAFT = "draft"
    COMPILED = "compiled"
    ACTIVE = "active"
    ERROR = "error"


class RenderSpace(Enum):
    """The coordinate space in which a graph's particles are simulated."""

    WORLD_SPACE = "world_space"
    LOCAL_SPACE = "local_space"
    SCREEN_SPACE = "screen_space"


class BlendMode(Enum):
    """The blending mode used when rendering a graph's particles.

    - ``ADDITIVE``: sum source and destination (bright fire/spark effects).
    - ``ALPHA_BLEND``: standard alpha transparency.
    - ``MULTIPLICATIVE``: multiply source and destination (darkening).
    - ``SUBTRACTIVE``: subtract source from destination.
    """

    ADDITIVE = "additive"
    ALPHA_BLEND = "alpha_blend"
    MULTIPLICATIVE = "multiplicative"
    SUBTRACTIVE = "subtractive"


class SortingMode(Enum):
    """How particles are sorted before rendering.

    - ``BY_DISTANCE``: back-to-front by distance to camera.
    - ``BY_AGE``: by particle age.
    - ``BY_INDEX``: by emission order.
    - ``UNSORTED``: no explicit sorting (fastest).
    """

    BY_DISTANCE = "by_distance"
    BY_AGE = "by_age"
    BY_INDEX = "by_index"
    UNSORTED = "unsorted"


class VFXEventKind(Enum):
    """Audit event kinds emitted by the VFX graph engine."""

    GRAPH_CREATED = "graph_created"
    GRAPH_UPDATED = "graph_updated"
    GRAPH_COMPILED = "graph_compiled"
    GRAPH_ACTIVATED = "graph_activated"
    NODE_ADDED = "node_added"
    NODE_REMOVED = "node_removed"
    CONNECTION_ADDED = "connection_added"
    CONNECTION_REMOVED = "connection_removed"
    PARAMETER_SET = "parameter_set"
    SUBGRAPH_INSTANCED = "subgraph_instanced"


# ---------------------------------------------------------------------------
# Default Pin Table
# ---------------------------------------------------------------------------

# Maps a VFXNodeType to the list of default pins that should be created
# automatically when a node of that type is added to a graph. Each entry
# is a tuple of (name, kind, data_type, default_value).
_PIN_DEFAULTS: Dict[VFXNodeType, List[Tuple[str, VFXPinKind, VFXDataType, Any]]] = {
    VFXNodeType.EMITTER: [
        ("particles", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("rate", VFXPinKind.INPUT, VFXDataType.FLOAT, 10.0),
        ("lifetime", VFXPinKind.INPUT, VFXDataType.FLOAT, 5.0),
    ],
    VFXNodeType.PARTICLE_INIT: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("initial_position", VFXPinKind.INPUT, VFXDataType.VECTOR3, [0.0, 0.0, 0.0]),
        ("initial_velocity", VFXPinKind.INPUT, VFXDataType.VECTOR3, [0.0, 0.0, 0.0]),
    ],
    VFXNodeType.FORCE_FIELD: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("force_direction", VFXPinKind.INPUT, VFXDataType.VECTOR3, [0.0, 1.0, 0.0]),
        ("strength", VFXPinKind.INPUT, VFXDataType.FLOAT, 1.0),
    ],
    VFXNodeType.COLLIDER: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("collider_shape", VFXPinKind.INPUT, VFXDataType.VECTOR3, [0.0, 0.0, 0.0]),
    ],
    VFXNodeType.COLOR_GRADIENT: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("color_gradient", VFXPinKind.INPUT, VFXDataType.GRADIENT, None),
    ],
    VFXNodeType.SIZE_CURVE: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("size_curve", VFXPinKind.INPUT, VFXDataType.CURVE, None),
    ],
    VFXNodeType.ROTATION_MOD: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("rotation_speed", VFXPinKind.INPUT, VFXDataType.FLOAT, 0.0),
    ],
    VFXNodeType.VELOCITY_MOD: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("velocity_scale", VFXPinKind.INPUT, VFXDataType.FLOAT, 1.0),
    ],
    VFXNodeType.LIFETIME_MOD: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("lifetime_scale", VFXPinKind.INPUT, VFXDataType.FLOAT, 1.0),
    ],
    VFXNodeType.TRAIL: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("trail_length", VFXPinKind.INPUT, VFXDataType.FLOAT, 1.0),
    ],
    VFXNodeType.NOISE_FIELD: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
        ("intensity", VFXPinKind.INPUT, VFXDataType.FLOAT, 1.0),
        ("scale", VFXPinKind.INPUT, VFXDataType.FLOAT, 1.0),
    ],
    VFXNodeType.RENDERER: [
        ("particles", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("texture", VFXPinKind.INPUT, VFXDataType.TEXTURE, None),
    ],
    VFXNodeType.SUBGRAPH: [
        ("in", VFXPinKind.INPUT, VFXDataType.PARTICLE_STREAM, None),
        ("out", VFXPinKind.OUTPUT, VFXDataType.PARTICLE_STREAM, None),
    ],
    VFXNodeType.MATH_OP: [
        ("a", VFXPinKind.INPUT, VFXDataType.FLOAT, 0.0),
        ("b", VFXPinKind.INPUT, VFXDataType.FLOAT, 0.0),
        ("result", VFXPinKind.OUTPUT, VFXDataType.FLOAT, None),
    ],
    VFXNodeType.PARAMETER: [
        ("value", VFXPinKind.OUTPUT, VFXDataType.FLOAT, 0.0),
    ],
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class VFXPin:
    """A connection point on a VFX node.

    Pins are the only places where data enters or leaves a node. An
    INPUT pin accepts data from exactly one source pin; an OUTPUT pin
    may feed one or more input pins. The ``connected_to`` list stores
    references to the pins currently connected to this pin, formatted as
    ``"node_id:pin_id"``.

    Attributes:
        pin_id: Unique identifier for the pin.
        name: Human-readable name of the pin (e.g. "particles", "rate").
        kind: The directional role of the pin.
        data_type: The data classification carried by the pin.
        default_value: The value used when the pin is not connected.
        connected_to: List of pin references connected to this pin.
        metadata: Free-form extension data.
    """

    pin_id: str = field(default_factory=lambda: _new_id("pin"))
    name: str = ""
    kind: VFXPinKind = VFXPinKind.INPUT
    data_type: VFXDataType = VFXDataType.FLOAT
    default_value: Any = None
    connected_to: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pin_id": self.pin_id,
            "name": self.name,
            "kind": self.kind.value,
            "data_type": self.data_type.value,
            "default_value": self.default_value,
            "connected_to": list(self.connected_to),
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class VFXNode:
    """A single operation within a VFX graph.

    A node owns a set of pins (inputs and outputs), a free-form
    parameters dictionary for operation-specific settings, a 2D editor
    position, and an enabled flag. Disabled nodes are skipped during
    compilation and runtime evaluation.

    Attributes:
        node_id: Unique identifier for the node.
        node_type: The VFXNodeType classification.
        name: Human-readable name of the node.
        position_x: Horizontal editor position.
        position_y: Vertical editor position.
        pins: List of VFXPin objects on this node.
        parameters: Operation-specific parameter dictionary.
        enabled: Whether the node is active during evaluation.
        metadata: Free-form extension data.
    """

    node_id: str = field(default_factory=lambda: _new_id("node"))
    node_type: VFXNodeType = VFXNodeType.EMITTER
    name: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    pins: List[VFXPin] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "pins": [p.to_dict() for p in self.pins],
            "parameters": dict(self.parameters) if self.parameters else {},
            "enabled": self.enabled,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class VFXConnection:
    """A typed edge linking an output pin to an input pin.

    A connection records the source node/pin, the target node/pin and
    the data type that flows across the edge. The data type is captured
    at connection time so that downstream type checks do not need to
    re-resolve the source pin.

    Attributes:
        connection_id: Unique identifier for the connection.
        source_node_id: Identifier of the node owning the source pin.
        source_pin_id: Identifier of the source (output) pin.
        target_node_id: Identifier of the node owning the target pin.
        target_pin_id: Identifier of the target (input) pin.
        data_type: The data classification flowing across the edge.
    """

    connection_id: str = field(default_factory=lambda: _new_id("conn"))
    source_node_id: str = ""
    source_pin_id: str = ""
    target_node_id: str = ""
    target_pin_id: str = ""
    data_type: VFXDataType = VFXDataType.PARTICLE_STREAM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "source_node_id": self.source_node_id,
            "source_pin_id": self.source_pin_id,
            "target_node_id": self.target_node_id,
            "target_pin_id": self.target_pin_id,
            "data_type": self.data_type.value,
        }


@dataclass
class VFXParameter:
    """An exposed, tunable parameter on a VFX graph.

    Parameters allow designers to expose named, typed values that can be
    overridden per instance at runtime (for example, the emission rate
    of a fire effect or its height). When ``min_value`` and
    ``max_value`` are both set the value is clamped to that range.

    Attributes:
        param_id: Unique identifier for the parameter.
        name: Programmatic name of the parameter.
        display_name: Human-readable label shown in the editor.
        param_type: The value type (e.g. "float", "int", "color").
        value: The current value.
        min_value: Optional inclusive lower bound for clamping.
        max_value: Optional inclusive upper bound for clamping.
        default_value: The value the parameter resets to.
        exposed: Whether the parameter is exposed for per-instance override.
        metadata: Free-form extension data.
    """

    param_id: str = field(default_factory=lambda: _new_id("param"))
    name: str = ""
    display_name: str = ""
    param_type: str = "float"
    value: Any = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_value: Any = 0.0
    exposed: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_id": self.param_id,
            "name": self.name,
            "display_name": self.display_name,
            "param_type": self.param_type,
            "value": self.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "default_value": self.default_value,
            "exposed": self.exposed,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class VFXGraph:
    """A complete VFX graph: a DAG of nodes and connections.

    A graph owns its nodes (keyed by node id), a list of connections
    between node pins, a list of exposed parameters, and the rendering
    configuration (render space, blend mode, sorting mode, particle
    budget, duration and looping).

    Attributes:
        graph_id: Unique identifier for the graph.
        name: Human-readable name of the graph.
        description: Long-form description of the graph.
        nodes: Mapping of node id to VFXNode.
        connections: List of VFXConnection edges.
        parameters: List of VFXParameter exposed values.
        status: The current GraphStatus.
        render_space: The coordinate space for simulation.
        blend_mode: The blending mode for rendering.
        sorting_mode: The particle sort order.
        max_particles: Maximum simultaneous particles.
        duration: Total duration in seconds (0.0 = infinite).
        loop: Whether the effect loops when duration elapses.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        metadata: Free-form extension data.
    """

    graph_id: str = field(default_factory=lambda: _new_id("graph"))
    name: str = ""
    description: str = ""
    nodes: Dict[str, VFXNode] = field(default_factory=dict)
    connections: List[VFXConnection] = field(default_factory=list)
    parameters: List[VFXParameter] = field(default_factory=list)
    status: GraphStatus = GraphStatus.DRAFT
    render_space: RenderSpace = RenderSpace.WORLD_SPACE
    blend_mode: BlendMode = BlendMode.ADDITIVE
    sorting_mode: SortingMode = SortingMode.BY_DISTANCE
    max_particles: int = 1000
    duration: float = 0.0
    loop: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "connections": [c.to_dict() for c in self.connections],
            "parameters": [p.to_dict() for p in self.parameters],
            "status": self.status.value,
            "render_space": self.render_space.value,
            "blend_mode": self.blend_mode.value,
            "sorting_mode": self.sorting_mode.value,
            "max_particles": self.max_particles,
            "duration": self.duration,
            "loop": self.loop,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class VFXGraphInstance:
    """A runtime instantiation of a compiled VFX graph.

    An instance places a compiled graph into the world at a specific
    position, rotation and scale, with optional per-instance parameter
    overrides. Instances start active and can be stopped (deactivated)
    when their effect is no longer needed.

    Attributes:
        instance_id: Unique identifier for the instance.
        graph_id: Identifier of the compiled graph being instantiated.
        position_x: World/local X position.
        position_y: World/local Y position.
        position_z: World/local Z position.
        rotation_x: X-axis rotation in degrees.
        rotation_y: Y-axis rotation in degrees.
        rotation_z: Z-axis rotation in degrees.
        scale: Uniform scale multiplier.
        parameter_overrides: Mapping of param name to overridden value.
        active: Whether the instance is currently running.
        started_at: ISO-8601 timestamp when the instance was started.
    """

    instance_id: str = field(default_factory=lambda: _new_id("inst"))
    graph_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    scale: float = 1.0
    parameter_overrides: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    started_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "graph_id": self.graph_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "position_z": self.position_z,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "rotation_z": self.rotation_z,
            "scale": self.scale,
            "parameter_overrides": dict(self.parameter_overrides)
            if self.parameter_overrides
            else {},
            "active": self.active,
            "started_at": self.started_at,
        }


@dataclass
class VFXCompileResult:
    """The outcome of validating and compiling a VFX graph.

    A successful compile (``success == True`` with no errors) sets the
    graph's status to COMPILED; otherwise the status is set to ERROR.
    Warnings are non-fatal observations about potentially incomplete
    graphs (for example unconnected input pins).

    Attributes:
        graph_id: Identifier of the compiled graph.
        success: Whether the compile succeeded (no errors).
        errors: List of fatal error messages.
        warnings: List of non-fatal warning messages.
        node_count: Number of nodes in the graph at compile time.
        connection_count: Number of connections in the graph at compile time.
        compiled_at: ISO-8601 timestamp of the compile.
    """

    graph_id: str = ""
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    node_count: int = 0
    connection_count: int = 0
    compiled_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "success": self.success,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "node_count": self.node_count,
            "connection_count": self.connection_count,
            "compiled_at": self.compiled_at,
        }


@dataclass
class VFXGraphStats:
    """Aggregate counters describing the VFX graph engine state.

    Attributes:
        total_graphs: Number of registered graphs.
        total_instances: Number of runtime instances.
        total_nodes: Total number of nodes across all graphs.
        total_connections: Total number of connections across all graphs.
        graphs_by_status: Mapping of status value to graph count.
        avg_nodes_per_graph: Average nodes per graph.
    """

    total_graphs: int = 0
    total_instances: int = 0
    total_nodes: int = 0
    total_connections: int = 0
    graphs_by_status: Dict[str, int] = field(default_factory=dict)
    avg_nodes_per_graph: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_graphs": self.total_graphs,
            "total_instances": self.total_instances,
            "total_nodes": self.total_nodes,
            "total_connections": self.total_connections,
            "graphs_by_status": dict(self.graphs_by_status)
            if self.graphs_by_status
            else {},
            "avg_nodes_per_graph": self.avg_nodes_per_graph,
        }


@dataclass
class VFXGraphSnapshot:
    """An immutable snapshot of the entire VFX graph engine state.

    Attributes:
        initialized: Whether the engine has completed initialization.
        graphs: List of all registered graphs.
        instances: List of all runtime instances.
        compile_results: List of the latest compile results per graph.
        events: List of all audit events.
        stats: Aggregate statistics.
    """

    initialized: bool = False
    graphs: List[VFXGraph] = field(default_factory=list)
    instances: List[VFXGraphInstance] = field(default_factory=list)
    compile_results: List[VFXCompileResult] = field(default_factory=list)
    events: List["VFXGraphEvent"] = field(default_factory=list)
    stats: VFXGraphStats = field(default_factory=VFXGraphStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "graphs": [g.to_dict() for g in self.graphs],
            "instances": [i.to_dict() for i in self.instances],
            "compile_results": [c.to_dict() for c in self.compile_results],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class VFXGraphEvent:
    """An audit event emitted by the VFX graph engine.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The VFXEventKind classification.
        timestamp: ISO-8601 timestamp when the event occurred.
        payload: Event-specific payload data.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: VFXEventKind = VFXEventKind.GRAPH_CREATED
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


# ---------------------------------------------------------------------------
# VFX Graph Engine (Singleton)
# ---------------------------------------------------------------------------


class VFXGraphEngine:
    """Node-based composable VFX graph orchestration engine.

    Maintains the registry of VFX graphs, runtime instances, compile
    results and audit events. Graphs are DAGs of nodes connected by
    typed pins; the engine validates connections for type compatibility
    and cycle freedom, compiles graphs for instantiation, and tracks
    running instances.

    The class implements the singleton pattern with double-checked
    locking using ``threading.RLock`` for thread-safe access. All
    public methods are guarded by the re-entrant lock. Consumers should
    obtain the instance through :meth:`get_instance` or the module-level
    :func:`get_vfx_graph` factory.

    Usage:
        engine = get_vfx_graph()
        graph = engine.create_graph("Fire Effect", blend_mode=BlendMode.ADDITIVE)
        emitter = engine.add_node(graph.graph_id, VFXNodeType.EMITTER, "Emitter")
        renderer = engine.add_node(graph.graph_id, VFXNodeType.RENDERER, "Renderer")
        engine.compile_graph(graph.graph_id)
        instance = engine.instantiate_graph(graph.graph_id)
    """

    _instance: Optional["VFXGraphEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "VFXGraphEngine":
        # Double-checked locking: acquire the lock only when the
        # instance has not yet been created. The freshly allocated
        # instance is marked as not-yet-initialized so that __init__
        # performs the real one-time setup.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(
        cls, instance_id: Optional[str] = None
    ) -> "Union[VFXGraphEngine, Optional[VFXGraphInstance]]":
        """Return the singleton engine, or a specific graph instance.

        When called with no arguments (or ``instance_id=None``) this
        returns the singleton :class:`VFXGraphEngine` instance. When
        called with an ``instance_id`` it returns the matching
        :class:`VFXGraphInstance` or ``None`` if not found.

        Does not reset the ``_initialized`` flag; only constructs the
        engine if it has not been created yet.

        Args:
            instance_id: Optional identifier of a runtime instance to
                look up. When None the singleton engine is returned.

        Returns:
            The singleton VFXGraphEngine when ``instance_id`` is None,
            otherwise the matching VFXGraphInstance or None.
        """
        if cls._instance is None:
            cls._instance = cls()
        if instance_id is not None:
            with cls._instance._lock:
                return cls._instance._instances.get(instance_id)
        return cls._instance

    def __init__(self) -> None:
        # One-time initialization guard. The outer check avoids taking
        # the lock on the hot path once initialization is complete; the
        # inner check prevents a race between two threads that both
        # observed _initialized as False.
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Primary registries.
            # Graphs keyed by graph id.
            self._graphs: Dict[str, VFXGraph] = {}
            # Runtime instances keyed by instance id.
            self._instances: Dict[str, VFXGraphInstance] = {}
            # Latest compile result per graph, keyed by graph id.
            self._compile_results: Dict[str, VFXCompileResult] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: List[VFXGraphEvent] = []

            # Aggregate counters maintained for fast stats retrieval.
            self._graph_counter: int = 0
            self._node_counter: int = 0
            self._connection_counter: int = 0
            self._parameter_counter: int = 0
            self._instance_counter: int = 0
            self._compile_counter: int = 0
            self._event_counter: int = 0

            self._initialized: bool = True

            # Populate the default seed VFX data.
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with two seed VFX graphs and one instance.

        The seed data demonstrates a typical particle-effect authoring
        workflow:

          1. "Fire Effect" -- a fully compiled additive-blended fire
             effect chaining an emitter through initialization, an
             upward force field, a red-to-yellow color gradient, a
             shrink-over-time size curve and a renderer. Two exposed
             parameters (emission_rate and fire_height) allow per-
             instance tuning, and one runtime instance is started at
             the world origin.
          2. "Magic Aura" -- a draft alpha-blended aura effect chaining
             an emitter through a noise field, a blue-to-purple color
             gradient and a renderer. Left in DRAFT status to
             illustrate the not-yet-compiled state.
        """
        # ------------------------------------------------------------------
        # Graph 1: Fire Effect (COMPILED, ADDITIVE, WORLD_SPACE).
        # ------------------------------------------------------------------
        fire = self.create_graph(
            name="Fire Effect",
            description=(
                "A warm fire effect: particles emit from a point, "
                "accelerate upward, fade from red to yellow, shrink "
                "over their lifetime and render additively."
            ),
            render_space=RenderSpace.WORLD_SPACE,
            blend_mode=BlendMode.ADDITIVE,
            sorting_mode=SortingMode.BY_DISTANCE,
            max_particles=500,
            duration=0.0,
            loop=True,
            metadata={"seed": True, "category": "fire"},
        )
        fire_id = fire.graph_id

        # Nodes laid out left-to-right for a clean editor layout.
        emitter = self.add_node(
            fire_id,
            VFXNodeType.EMITTER,
            name="Fire Emitter",
            position_x=0.0,
            position_y=0.0,
            parameters={"shape": "point", "rate": 50.0},
            metadata={"seed": True},
        )
        pinit = self.add_node(
            fire_id,
            VFXNodeType.PARTICLE_INIT,
            name="Particle Init",
            position_x=220.0,
            position_y=0.0,
            parameters={
                "initial_position": [0.0, 0.0, 0.0],
                "initial_velocity": [0.0, 1.0, 0.0],
            },
            metadata={"seed": True},
        )
        force = self.add_node(
            fire_id,
            VFXNodeType.FORCE_FIELD,
            name="Upward Force",
            position_x=440.0,
            position_y=0.0,
            parameters={
                "force_direction": [0.0, 1.0, 0.0],
                "strength": 3.0,
            },
            metadata={"seed": True, "description": "upward force"},
        )
        color = self.add_node(
            fire_id,
            VFXNodeType.COLOR_GRADIENT,
            name="Red->Yellow Gradient",
            position_x=660.0,
            position_y=0.0,
            parameters={"gradient": [[1.0, 0.0, 0.0, 1.0], [1.0, 1.0, 0.0, 1.0]]},
            metadata={"seed": True, "description": "red->yellow"},
        )
        size = self.add_node(
            fire_id,
            VFXNodeType.SIZE_CURVE,
            name="Shrink Over Time",
            position_x=880.0,
            position_y=0.0,
            parameters={"curve": [[0.0, 1.0], [1.0, 0.1]]},
            metadata={"seed": True, "description": "shrink over time"},
        )
        renderer = self.add_node(
            fire_id,
            VFXNodeType.RENDERER,
            name="Fire Renderer",
            position_x=1100.0,
            position_y=0.0,
            parameters={"material": "particles/fire_additive"},
            metadata={"seed": True},
        )

        # Connections: emitter -> init -> force -> color -> size -> renderer.
        self._connect_by_name(fire_id, emitter, "particles", pinit, "in")
        self._connect_by_name(fire_id, pinit, "out", force, "in")
        self._connect_by_name(fire_id, force, "out", color, "in")
        self._connect_by_name(fire_id, color, "out", size, "in")
        self._connect_by_name(fire_id, size, "out", renderer, "particles")

        # Exposed parameters for per-instance tuning.
        self.add_parameter(
            fire_id,
            name="emission_rate",
            display_name="Emission Rate",
            param_type="float",
            value=50.0,
            min_value=0.0,
            max_value=500.0,
            exposed=True,
        )
        self.add_parameter(
            fire_id,
            name="fire_height",
            display_name="Fire Height",
            param_type="float",
            value=3.0,
            min_value=0.1,
            max_value=20.0,
            exposed=True,
        )

        # Compile so the graph can be instantiated.
        self.compile_graph(fire_id)

        # Start one runtime instance at the world origin.
        self.instantiate_graph(
            fire_id,
            position_x=0.0,
            position_y=0.0,
            position_z=0.0,
        )

        # ------------------------------------------------------------------
        # Graph 2: Magic Aura (DRAFT, ALPHA_BLEND, WORLD_SPACE).
        # ------------------------------------------------------------------
        aura = self.create_graph(
            name="Magic Aura",
            description=(
                "A mystical aura effect: particles drift through a "
                "noise field and fade from blue to purple before "
                "rendering with alpha blending. Left in DRAFT status."
            ),
            render_space=RenderSpace.WORLD_SPACE,
            blend_mode=BlendMode.ALPHA_BLEND,
            sorting_mode=SortingMode.BY_DISTANCE,
            max_particles=200,
            duration=0.0,
            loop=True,
            metadata={"seed": True, "category": "magic"},
        )
        aura_id = aura.graph_id

        aura_emitter = self.add_node(
            aura_id,
            VFXNodeType.EMITTER,
            name="Aura Emitter",
            position_x=0.0,
            position_y=0.0,
            parameters={"shape": "sphere", "rate": 20.0, "radius": 1.5},
            metadata={"seed": True},
        )
        noise = self.add_node(
            aura_id,
            VFXNodeType.NOISE_FIELD,
            name="Drift Noise",
            position_x=220.0,
            position_y=0.0,
            parameters={"intensity": 0.5, "scale": 2.0},
            metadata={"seed": True},
        )
        aura_color = self.add_node(
            aura_id,
            VFXNodeType.COLOR_GRADIENT,
            name="Blue->Purple Gradient",
            position_x=440.0,
            position_y=0.0,
            parameters={
                "gradient": [[0.0, 0.0, 1.0, 1.0], [0.5, 0.0, 0.5, 1.0]]
            },
            metadata={"seed": True, "description": "blue->purple"},
        )
        aura_renderer = self.add_node(
            aura_id,
            VFXNodeType.RENDERER,
            name="Aura Renderer",
            position_x=660.0,
            position_y=0.0,
            parameters={"material": "particles/aura_alpha"},
            metadata={"seed": True},
        )

        # Connections: emitter -> noise -> color -> renderer.
        self._connect_by_name(aura_id, aura_emitter, "particles", noise, "in")
        self._connect_by_name(aura_id, noise, "out", aura_color, "in")
        self._connect_by_name(aura_id, aura_color, "out", aura_renderer, "particles")

        # Intentionally left in DRAFT status (not compiled).

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect_by_name(
        self,
        graph_id: str,
        source_node: VFXNode,
        source_pin_name: str,
        target_node: VFXNode,
        target_pin_name: str,
    ) -> Optional[VFXConnection]:
        """Connect two pins by name (helper used during seeding).

        Looks up the source and target pins by name on the provided
        nodes and delegates to :meth:`connect`.

        Args:
            graph_id: Identifier of the graph.
            source_node: The source VFXNode object.
            source_pin_name: Name of the source pin.
            target_node: The target VFXNode object.
            target_pin_name: Name of the target pin.

        Returns:
            The created VFXConnection, or None if a pin could not be
            found or the connection was rejected.
        """
        source_pin = self._find_pin_by_name(source_node, source_pin_name)
        target_pin = self._find_pin_by_name(target_node, target_pin_name)
        if source_pin is None or target_pin is None:
            return None
        return self.connect(
            graph_id,
            source_node.node_id,
            source_pin.pin_id,
            target_node.node_id,
            target_pin.pin_id,
        )

    @staticmethod
    def _find_pin_by_name(node: VFXNode, name: str) -> Optional[VFXPin]:
        """Return the first pin on a node with the given name.

        Args:
            node: The VFXNode to search.
            name: The pin name to match.

        Returns:
            The matching VFXPin, or None if not found.
        """
        for pin in node.pins:
            if pin.name == name:
                return pin
        return None

    @staticmethod
    def _find_pin(node: VFXNode, pin_id: str) -> Optional[VFXPin]:
        """Return the pin on a node with the given pin id.

        Args:
            node: The VFXNode to search.
            pin_id: The pin identifier to match.

        Returns:
            The matching VFXPin, or None if not found.
        """
        for pin in node.pins:
            if pin.pin_id == pin_id:
                return pin
        return None

    @staticmethod
    def _would_create_cycle(
        graph: VFXGraph, source_node_id: str, target_node_id: str
    ) -> bool:
        """Check if adding an edge source->target would create a cycle.

        A cycle is created when the target node can already reach the
        source node through existing edges (including the trivial case
        of a self-loop where source == target).

        Args:
            graph: The graph to inspect.
            source_node_id: The prospective edge's source node.
            target_node_id: The prospective edge's target node.

        Returns:
            True if adding the edge would create a cycle.
        """
        # A self-loop is always a cycle.
        if source_node_id == target_node_id:
            return True
        # Depth-first search from the target following existing edges
        # (source -> target direction). If we ever reach the prospective
        # source node then a path target->...->source already exists and
        # adding source->target would close the loop.
        visited: set = set()
        stack: List[str] = [target_node_id]
        while stack:
            current = stack.pop()
            if current == source_node_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            for conn in graph.connections:
                if conn.source_node_id == current:
                    if conn.target_node_id not in visited:
                        stack.append(conn.target_node_id)
        return False

    def _record_event(
        self,
        kind: VFXEventKind,
        payload: Dict[str, Any],
    ) -> VFXGraphEvent:
        """Record an audit event (caller must hold ``self._lock``).

        Args:
            kind: The VFXEventKind classification.
            payload: Event-specific payload data.

        Returns:
            The created VFXGraphEvent.
        """
        event = VFXGraphEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        if len(self._events) >= _MAX_EVENTS:
            # FIFO eviction: drop the oldest event.
            self._events.pop(0)
        self._events.append(event)
        self._event_counter += 1
        return event

    # ------------------------------------------------------------------
    # Graph management
    # ------------------------------------------------------------------

    def create_graph(
        self,
        name: str,
        description: str = "",
        render_space: RenderSpace = RenderSpace.WORLD_SPACE,
        blend_mode: BlendMode = BlendMode.ADDITIVE,
        sorting_mode: SortingMode = SortingMode.BY_DISTANCE,
        max_particles: int = 1000,
        duration: float = 0.0,
        loop: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VFXGraph:
        """Create a new VFX graph.

        Args:
            name: Human-readable name of the graph.
            description: Long-form description of the graph.
            render_space: The coordinate space for simulation.
            blend_mode: The blending mode for rendering.
            sorting_mode: The particle sort order.
            max_particles: Maximum simultaneous particles.
            duration: Total duration in seconds (0.0 = infinite).
            loop: Whether the effect loops when duration elapses.
            metadata: Optional free-form extension data.

        Returns:
            The newly created VFXGraph (in DRAFT status).
        """
        with self._lock:
            # Enforce the bounded store cap via FIFO eviction.
            if len(self._graphs) >= _MAX_GRAPHS:
                oldest_id = next(iter(self._graphs), None)
                if oldest_id is not None:
                    self._delete_graph_internal(oldest_id)

            graph = VFXGraph(
                name=name,
                description=description,
                render_space=render_space,
                blend_mode=blend_mode,
                sorting_mode=sorting_mode,
                max_particles=int(max_particles),
                duration=float(duration),
                loop=bool(loop),
                metadata=dict(metadata) if metadata else {},
            )
            self._graphs[graph.graph_id] = graph
            self._graph_counter += 1

            self._record_event(
                VFXEventKind.GRAPH_CREATED,
                payload={
                    "graph_id": graph.graph_id,
                    "name": graph.name,
                    "blend_mode": graph.blend_mode.value,
                    "render_space": graph.render_space.value,
                    "max_particles": graph.max_particles,
                },
            )
            return graph

    def get_graph(self, graph_id: str) -> Optional[VFXGraph]:
        """Return the graph with the given identifier.

        Args:
            graph_id: The unique identifier of the graph.

        Returns:
            The matching VFXGraph, or None if not found.
        """
        with self._lock:
            return self._graphs.get(graph_id)

    def list_graphs(self, status: Optional[GraphStatus] = None) -> List[VFXGraph]:
        """List registered graphs, optionally filtered by status.

        Args:
            status: Optional status to filter by.

        Returns:
            A list of VFXGraph objects matching the filter.
        """
        with self._lock:
            graphs = list(self._graphs.values())
        if status is None:
            return graphs
        return [g for g in graphs if g.status == status]

    def update_graph(self, graph_id: str, **kwargs: Any) -> Optional[VFXGraph]:
        """Update any graph fields by keyword arguments.

        Accepts name, description, render_space, blend_mode,
        sorting_mode, max_particles, duration, loop and metadata. The
        updated_at timestamp is refreshed, the status is reset to DRAFT
        (since the graph may no longer be valid), and a GRAPH_UPDATED
        event is recorded.

        Args:
            graph_id: The unique identifier of the graph.
            **kwargs: Field names mapped to their new values.

        Returns:
            The updated VFXGraph, or None if not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            # Whitelisted mutable fields that may be updated via kwargs.
            allowed_fields = {
                "name",
                "description",
                "render_space",
                "blend_mode",
                "sorting_mode",
                "max_particles",
                "duration",
                "loop",
                "metadata",
            }
            changed = False
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                setattr(graph, key, value)
                changed = True

            if changed:
                graph.updated_at = _now()
                # Editing a compiled/error graph invalidates its status.
                if graph.status in (GraphStatus.COMPILED, GraphStatus.ERROR):
                    graph.status = GraphStatus.DRAFT
                self._record_event(
                    VFXEventKind.GRAPH_UPDATED,
                    payload={
                        "graph_id": graph_id,
                        "updated_fields": [k for k in kwargs if k in allowed_fields],
                    },
                )
            return graph

    def _delete_graph_internal(self, graph_id: str) -> bool:
        """Delete a graph and its associated data (caller holds lock).

        Removes the graph, its compile result, and any runtime
        instances that reference it.

        Args:
            graph_id: The unique identifier of the graph.

        Returns:
            True if the graph was removed, False if it was not found.
        """
        if graph_id not in self._graphs:
            return False
        self._graphs.pop(graph_id, None)
        # Remove the latest compile result for the graph.
        self._compile_results.pop(graph_id, None)
        # Remove any runtime instances referencing the deleted graph.
        orphan_ids = [
            iid
            for iid, inst in self._instances.items()
            if inst.graph_id == graph_id
        ]
        for iid in orphan_ids:
            self._instances.pop(iid, None)
        return True

    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph and its associated data.

        Removes the graph, its compile result, and any runtime
        instances that reference it. Records a GRAPH_UPDATED event.

        Args:
            graph_id: The unique identifier of the graph.

        Returns:
            True if the graph was removed, False if it was not found.
        """
        with self._lock:
            removed = self._delete_graph_internal(graph_id)
            if removed:
                self._record_event(
                    VFXEventKind.GRAPH_UPDATED,
                    payload={"graph_id": graph_id, "deleted": True},
                )
            return removed

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(
        self,
        graph_id: str,
        node_type: VFXNodeType,
        name: str = "",
        position_x: float = 0.0,
        position_y: float = 0.0,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[VFXNode]:
        """Add a node to a graph, automatically creating default pins.

        The default pins are derived from the node type via the
        ``_PIN_DEFAULTS`` table. Each pin receives a unique id so it can
        be referenced by connections.

        Args:
            graph_id: Identifier of the graph to add the node to.
            node_type: The VFXNodeType classification.
            name: Human-readable name of the node.
            position_x: Horizontal editor position.
            position_y: Vertical editor position.
            parameters: Optional operation-specific parameters.
            metadata: Optional free-form extension data.

        Returns:
            The newly created VFXNode, or None if the graph was not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            # Build the default pins for this node type.
            pin_specs = _PIN_DEFAULTS.get(node_type, [])
            pins: List[VFXPin] = []
            for pin_name, kind, data_type, default_value in pin_specs:
                pins.append(
                    VFXPin(
                        name=pin_name,
                        kind=kind,
                        data_type=data_type,
                        default_value=default_value,
                    )
                )

            node = VFXNode(
                node_type=node_type,
                name=name if name else node_type.value,
                position_x=float(position_x),
                position_y=float(position_y),
                pins=pins,
                parameters=dict(parameters) if parameters else {},
                metadata=dict(metadata) if metadata else {},
            )
            graph.nodes[node.node_id] = node
            graph.updated_at = _now()
            # Adding a node invalidates a previously compiled graph.
            if graph.status in (GraphStatus.COMPILED, GraphStatus.ERROR):
                graph.status = GraphStatus.DRAFT
            self._node_counter += 1

            self._record_event(
                VFXEventKind.NODE_ADDED,
                payload={
                    "graph_id": graph_id,
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "name": node.name,
                },
            )
            return node

    def get_node(self, graph_id: str, node_id: str) -> Optional[VFXNode]:
        """Return the node with the given identifier within a graph.

        Args:
            graph_id: The unique identifier of the graph.
            node_id: The unique identifier of the node.

        Returns:
            The matching VFXNode, or None if not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            return graph.nodes.get(node_id)

    def list_nodes(
        self,
        graph_id: str,
        node_type: Optional[VFXNodeType] = None,
    ) -> List[VFXNode]:
        """List nodes in a graph, optionally filtered by node type.

        Args:
            graph_id: Identifier of the graph.
            node_type: Optional node type to filter by.

        Returns:
            A list of VFXNode objects matching the filter.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return []
            nodes = list(graph.nodes.values())
        if node_type is None:
            return nodes
        return [n for n in nodes if n.node_type == node_type]

    def update_node(
        self,
        graph_id: str,
        node_id: str,
        **kwargs: Any,
    ) -> Optional[VFXNode]:
        """Update any node fields by keyword arguments.

        Accepts name, position_x, position_y, parameters, enabled and
        metadata. The graph's updated_at timestamp is refreshed and the
        graph status is reset to DRAFT if it was previously compiled.

        Args:
            graph_id: The unique identifier of the graph.
            node_id: The unique identifier of the node.
            **kwargs: Field names mapped to their new values.

        Returns:
            The updated VFXNode, or None if not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            node = graph.nodes.get(node_id)
            if node is None:
                return None

            # Whitelisted mutable fields that may be updated via kwargs.
            allowed_fields = {
                "name",
                "position_x",
                "position_y",
                "parameters",
                "enabled",
                "metadata",
            }
            changed = False
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                setattr(node, key, value)
                changed = True

            if changed:
                graph.updated_at = _now()
                if graph.status in (GraphStatus.COMPILED, GraphStatus.ERROR):
                    graph.status = GraphStatus.DRAFT
                self._record_event(
                    VFXEventKind.GRAPH_UPDATED,
                    payload={
                        "graph_id": graph_id,
                        "node_id": node_id,
                        "updated_fields": [
                            k for k in kwargs if k in allowed_fields
                        ],
                    },
                )
            return node

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        """Remove a node and all its connections from a graph.

        Args:
            graph_id: The unique identifier of the graph.
            node_id: The unique identifier of the node.

        Returns:
            True if the node was removed, False if it was not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False
            if node_id not in graph.nodes:
                return False

            # Remove every connection that references this node.
            graph.connections = [
                c
                for c in graph.connections
                if c.source_node_id != node_id and c.target_node_id != node_id
            ]
            graph.nodes.pop(node_id, None)
            graph.updated_at = _now()
            if graph.status in (GraphStatus.COMPILED, GraphStatus.ERROR):
                graph.status = GraphStatus.DRAFT
            self._record_event(
                VFXEventKind.NODE_REMOVED,
                payload={"graph_id": graph_id, "node_id": node_id},
            )
            return True

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(
        self,
        graph_id: str,
        source_node_id: str,
        source_pin_id: str,
        target_node_id: str,
        target_pin_id: str,
    ) -> Optional[VFXConnection]:
        """Connect two pins, validating type compatibility and cycles.

        The source pin must be an OUTPUT (or INOUT) pin and the target
        pin must be an INPUT (or INOUT) pin. The data types of the two
        pins must match exactly. An input pin may only have a single
        incoming connection; attempting to connect an already-connected
        input is rejected. Adding the edge must not create a cycle in
        the graph.

        Args:
            graph_id: Identifier of the graph.
            source_node_id: Identifier of the source node.
            source_pin_id: Identifier of the source (output) pin.
            target_node_id: Identifier of the target node.
            target_pin_id: Identifier of the target (input) pin.

        Returns:
            The created VFXConnection, or None if validation failed.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            source_node = graph.nodes.get(source_node_id)
            target_node = graph.nodes.get(target_node_id)
            if source_node is None or target_node is None:
                return None

            source_pin = self._find_pin(source_node, source_pin_id)
            target_pin = self._find_pin(target_node, target_pin_id)
            if source_pin is None or target_pin is None:
                return None

            # The source pin must be an output (or inout) producer.
            if source_pin.kind not in (VFXPinKind.OUTPUT, VFXPinKind.INOUT):
                return None
            # The target pin must be an input (or inout) consumer.
            if target_pin.kind not in (VFXPinKind.INPUT, VFXPinKind.INOUT):
                return None
            # The data types must match exactly.
            if source_pin.data_type != target_pin.data_type:
                return None
            # An input pin may only have a single incoming connection.
            if target_pin.connected_to:
                return None
            # Reject duplicate connections (same source -> same target).
            for conn in graph.connections:
                if (
                    conn.source_node_id == source_node_id
                    and conn.source_pin_id == source_pin_id
                    and conn.target_node_id == target_node_id
                    and conn.target_pin_id == target_pin_id
                ):
                    return None
            # Reject connections that would create a cycle.
            if self._would_create_cycle(graph, source_node_id, target_node_id):
                return None

            connection = VFXConnection(
                source_node_id=source_node_id,
                source_pin_id=source_pin_id,
                target_node_id=target_node_id,
                target_pin_id=target_pin_id,
                data_type=source_pin.data_type,
            )
            graph.connections.append(connection)
            # Update the pin connection references for both endpoints.
            source_ref = f"{source_node_id}:{source_pin_id}"
            target_ref = f"{target_node_id}:{target_pin_id}"
            if target_ref not in source_pin.connected_to:
                source_pin.connected_to.append(target_ref)
            if source_ref not in target_pin.connected_to:
                target_pin.connected_to.append(source_ref)
            graph.updated_at = _now()
            if graph.status in (GraphStatus.COMPILED, GraphStatus.ERROR):
                graph.status = GraphStatus.DRAFT
            self._connection_counter += 1

            self._record_event(
                VFXEventKind.CONNECTION_ADDED,
                payload={
                    "graph_id": graph_id,
                    "connection_id": connection.connection_id,
                    "source_node_id": source_node_id,
                    "source_pin_id": source_pin_id,
                    "target_node_id": target_node_id,
                    "target_pin_id": target_pin_id,
                    "data_type": connection.data_type.value,
                },
            )
            return connection

    def disconnect(self, graph_id: str, connection_id: str) -> bool:
        """Remove a connection from a graph.

        Args:
            graph_id: The unique identifier of the graph.
            connection_id: The unique identifier of the connection.

        Returns:
            True if the connection was removed, False if not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False

            connection: Optional[VFXConnection] = None
            for conn in graph.connections:
                if conn.connection_id == connection_id:
                    connection = conn
                    break
            if connection is None:
                return False

            graph.connections = [
                c for c in graph.connections if c.connection_id != connection_id
            ]
            # Clear the pin connection references on both endpoints.
            source_node = graph.nodes.get(connection.source_node_id)
            target_node = graph.nodes.get(connection.target_node_id)
            if source_node is not None:
                source_pin = self._find_pin(source_node, connection.source_pin_id)
                if source_pin is not None:
                    target_ref = f"{connection.target_node_id}:{connection.target_pin_id}"
                    if target_ref in source_pin.connected_to:
                        source_pin.connected_to.remove(target_ref)
            if target_node is not None:
                target_pin = self._find_pin(target_node, connection.target_pin_id)
                if target_pin is not None:
                    source_ref = f"{connection.source_node_id}:{connection.source_pin_id}"
                    if source_ref in target_pin.connected_to:
                        target_pin.connected_to.remove(source_ref)
            graph.updated_at = _now()
            if graph.status in (GraphStatus.COMPILED, GraphStatus.ERROR):
                graph.status = GraphStatus.DRAFT

            self._record_event(
                VFXEventKind.CONNECTION_REMOVED,
                payload={
                    "graph_id": graph_id,
                    "connection_id": connection_id,
                },
            )
            return True

    def list_connections(
        self,
        graph_id: str,
        node_id: Optional[str] = None,
    ) -> List[VFXConnection]:
        """List connections in a graph, optionally filtered by node.

        When ``node_id`` is provided, only connections where the node is
        either the source or the target are returned.

        Args:
            graph_id: Identifier of the graph.
            node_id: Optional node id to filter by.

        Returns:
            A list of VFXConnection objects matching the filter.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return []
            connections = list(graph.connections)
        if node_id is None:
            return connections
        return [
            c
            for c in connections
            if c.source_node_id == node_id or c.target_node_id == node_id
        ]

    # ------------------------------------------------------------------
    # Parameter management
    # ------------------------------------------------------------------

    def add_parameter(
        self,
        graph_id: str,
        name: str,
        display_name: str = "",
        param_type: str = "float",
        value: Any = 0.0,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        exposed: bool = True,
    ) -> Optional[VFXParameter]:
        """Add an exposed parameter to a graph.

        Args:
            graph_id: Identifier of the graph.
            name: Programmatic name of the parameter.
            display_name: Human-readable label shown in the editor.
            param_type: The value type (e.g. "float", "int", "color").
            value: The initial value.
            min_value: Optional inclusive lower bound for clamping.
            max_value: Optional inclusive upper bound for clamping.
            exposed: Whether the parameter is exposed for per-instance override.

        Returns:
            The newly created VFXParameter, or None if the graph was not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            # Clamp the initial value to the provided bounds.
            clamped_value = value
            if (
                isinstance(value, (int, float))
                and min_value is not None
                and max_value is not None
            ):
                clamped_value = _clamp(float(value), float(min_value), float(max_value))

            param = VFXParameter(
                name=name,
                display_name=display_name if display_name else name,
                param_type=param_type,
                value=clamped_value,
                min_value=min_value,
                max_value=max_value,
                default_value=clamped_value,
                exposed=bool(exposed),
            )
            graph.parameters.append(param)
            graph.updated_at = _now()
            self._parameter_counter += 1

            self._record_event(
                VFXEventKind.PARAMETER_SET,
                payload={
                    "graph_id": graph_id,
                    "param_id": param.param_id,
                    "name": param.name,
                    "value": param.value,
                    "added": True,
                },
            )
            return param

    def set_parameter(
        self,
        graph_id: str,
        param_id: str,
        value: Any,
    ) -> Optional[VFXParameter]:
        """Set the value of an existing graph parameter.

        When both ``min_value`` and ``max_value`` are defined on the
        parameter and the new value is numeric, the value is clamped to
        that range.

        Args:
            graph_id: Identifier of the graph.
            param_id: Identifier of the parameter.
            value: The new value.

        Returns:
            The updated VFXParameter, or None if not found.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            param: Optional[VFXParameter] = None
            for p in graph.parameters:
                if p.param_id == param_id:
                    param = p
                    break
            if param is None:
                return None

            # Clamp numeric values to the parameter bounds.
            new_value = value
            if (
                isinstance(value, (int, float))
                and param.min_value is not None
                and param.max_value is not None
            ):
                new_value = _clamp(
                    float(value),
                    float(param.min_value),
                    float(param.max_value),
                )
            param.value = new_value
            graph.updated_at = _now()

            self._record_event(
                VFXEventKind.PARAMETER_SET,
                payload={
                    "graph_id": graph_id,
                    "param_id": param_id,
                    "name": param.name,
                    "value": param.value,
                },
            )
            return param

    def list_parameters(self, graph_id: str) -> List[VFXParameter]:
        """List the exposed parameters of a graph.

        Args:
            graph_id: Identifier of the graph.

        Returns:
            A list of VFXParameter objects on the graph.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return []
            return list(graph.parameters)

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def compile_graph(self, graph_id: str) -> VFXCompileResult:
        """Validate a graph and set its status to COMPILED or ERROR.

        Validation checks:
          - Cycle detection across the full connection set (errors).
          - Type-mismatch detection on every connection (errors).
          - Unconnected input pins without default values (warnings).
          - Graphs without an emitter or a renderer (warnings).

        A successful compile (no errors) sets the graph status to
        COMPILED; otherwise the status is set to ERROR.

        Args:
            graph_id: Identifier of the graph to compile.

        Returns:
            A VFXCompileResult describing the outcome.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return VFXCompileResult(
                    graph_id=graph_id,
                    success=False,
                    errors=["graph not found"],
                    compiled_at=_now(),
                )

            errors: List[str] = []
            warnings: List[str] = []

            # 1. Verify that no cycles exist. Since connect() prevents
            #    cycles, this should always pass; but a future
            #    bulk-load path could bypass connect() so we check here
            #    for safety.
            if self._has_cycle(graph):
                errors.append("graph contains a cycle")

            # 2. Verify type compatibility on every connection.
            for conn in graph.connections:
                source_node = graph.nodes.get(conn.source_node_id)
                target_node = graph.nodes.get(conn.target_node_id)
                if source_node is None:
                    errors.append(
                        f"connection {conn.connection_id} references missing "
                        f"source node {conn.source_node_id}"
                    )
                    continue
                if target_node is None:
                    errors.append(
                        f"connection {conn.connection_id} references missing "
                        f"target node {conn.target_node_id}"
                    )
                    continue
                source_pin = self._find_pin(source_node, conn.source_pin_id)
                target_pin = self._find_pin(target_node, conn.target_pin_id)
                if source_pin is None or target_pin is None:
                    errors.append(
                        f"connection {conn.connection_id} references a missing pin"
                    )
                    continue
                if source_pin.data_type != target_pin.data_type:
                    errors.append(
                        f"connection {conn.connection_id} has a type mismatch: "
                        f"{source_pin.data_type.value} -> {target_pin.data_type.value}"
                    )
                if source_pin.data_type != conn.data_type:
                    errors.append(
                        f"connection {conn.connection_id} data_type "
                        f"({conn.data_type.value}) does not match the source "
                        f"pin ({source_pin.data_type.value})"
                    )

            # 3. Warn about unconnected input pins without defaults.
            connected_target_pins: set = set()
            for conn in graph.connections:
                connected_target_pins.add(
                    f"{conn.target_node_id}:{conn.target_pin_id}"
                )
            for node in graph.nodes.values():
                if not node.enabled:
                    continue
                for pin in node.pins:
                    if pin.kind in (VFXPinKind.INPUT, VFXPinKind.INOUT):
                        ref = f"{node.node_id}:{pin.pin_id}"
                        if ref not in connected_target_pins:
                            if pin.default_value is None:
                                warnings.append(
                                    f"node '{node.name}' input pin "
                                    f"'{pin.name}' is not connected and has "
                                    f"no default value"
                                )

            # 4. Warn about missing emitters or renderers.
            node_types = {n.node_type for n in graph.nodes.values()}
            if VFXNodeType.EMITTER not in node_types and graph.nodes:
                warnings.append("graph has no emitter node")
            if VFXNodeType.RENDERER not in node_types and graph.nodes:
                warnings.append("graph has no renderer node")

            success = not errors
            if success:
                graph.status = GraphStatus.COMPILED
            else:
                graph.status = GraphStatus.ERROR
            graph.updated_at = _now()

            result = VFXCompileResult(
                graph_id=graph_id,
                success=success,
                errors=errors,
                warnings=warnings,
                node_count=len(graph.nodes),
                connection_count=len(graph.connections),
                compiled_at=_now(),
            )
            # Store the latest compile result, evicting the oldest if at cap.
            if len(self._compile_results) >= _MAX_COMPILE_RESULTS:
                oldest_id = next(iter(self._compile_results), None)
                if oldest_id is not None:
                    self._compile_results.pop(oldest_id, None)
            self._compile_results[graph_id] = result
            self._compile_counter += 1

            self._record_event(
                VFXEventKind.GRAPH_COMPILED,
                payload={
                    "graph_id": graph_id,
                    "success": success,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "node_count": result.node_count,
                    "connection_count": result.connection_count,
                },
            )
            return result

    @staticmethod
    def _has_cycle(graph: VFXGraph) -> bool:
        """Detect whether the graph contains any cycle.

        Uses a depth-first traversal with a recursion-stack colouring:
        white (unvisited), grey (on the current path), black (fully
        explored). Encountering a grey node indicates a back edge and
        therefore a cycle.

        Args:
            graph: The graph to inspect.

        Returns:
            True if a cycle is present.
        """
        # Build the adjacency list from connections.
        adjacency: Dict[str, List[str]] = {}
        for node_id in graph.nodes:
            adjacency[node_id] = []
        for conn in graph.connections:
            adjacency.setdefault(conn.source_node_id, []).append(
                conn.target_node_id
            )

        white, grey, black = 0, 1, 2
        color: Dict[str, int] = {nid: white for nid in adjacency}

        def dfs(node_id: str) -> bool:
            color[node_id] = grey
            for neighbor in adjacency.get(node_id, []):
                if color.get(neighbor, white) == grey:
                    return True
                if color.get(neighbor, white) == white:
                    if dfs(neighbor):
                        return True
            color[node_id] = black
            return False

        for node_id in adjacency:
            if color[node_id] == white:
                if dfs(node_id):
                    return True
        return False

    # ------------------------------------------------------------------
    # Instance management
    # ------------------------------------------------------------------

    def instantiate_graph(
        self,
        graph_id: str,
        position_x: float = 0.0,
        position_y: float = 0.0,
        position_z: float = 0.0,
        parameter_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[VFXGraphInstance]:
        """Create a runtime instance of a compiled graph.

        Only graphs whose status is COMPILED (or ACTIVE) may be
        instantiated. The instance starts active and is placed at the
        given position with optional parameter overrides.

        Args:
            graph_id: Identifier of the compiled graph.
            position_x: World/local X position.
            position_y: World/local Y position.
            position_z: World/local Z position.
            parameter_overrides: Optional mapping of param name to value.

        Returns:
            The newly created VFXGraphInstance, or None if the graph
            was not found or not compiled.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            if graph.status not in (GraphStatus.COMPILED, GraphStatus.ACTIVE):
                return None

            # Enforce the bounded instance store cap via FIFO eviction.
            if len(self._instances) >= _MAX_INSTANCES:
                oldest_id = next(iter(self._instances), None)
                if oldest_id is not None:
                    self._instances.pop(oldest_id, None)

            instance = VFXGraphInstance(
                graph_id=graph_id,
                position_x=float(position_x),
                position_y=float(position_y),
                position_z=float(position_z),
                parameter_overrides=dict(parameter_overrides)
                if parameter_overrides
                else {},
            )
            self._instances[instance.instance_id] = instance
            # Promote the graph to ACTIVE now that it has a running instance.
            if graph.status == GraphStatus.COMPILED:
                graph.status = GraphStatus.ACTIVE
            self._instance_counter += 1

            self._record_event(
                VFXEventKind.SUBGRAPH_INSTANCED,
                payload={
                    "graph_id": graph_id,
                    "instance_id": instance.instance_id,
                    "position": [
                        instance.position_x,
                        instance.position_y,
                        instance.position_z,
                    ],
                },
            )
            return instance

    def get_instance_by_id(self, instance_id: str) -> Optional[VFXGraphInstance]:
        """Return the runtime instance with the given identifier.

        This is a thin convenience wrapper around the classmethod
        :meth:`get_instance` for callers who already hold an engine
        reference and prefer an explicitly named lookup.

        Args:
            instance_id: The unique identifier of the instance.

        Returns:
            The matching VFXGraphInstance, or None if not found.
        """
        with self._lock:
            return self._instances.get(instance_id)

    def list_instances(
        self,
        graph_id: Optional[str] = None,
        active_only: bool = False,
    ) -> List[VFXGraphInstance]:
        """List runtime instances, optionally filtered.

        Args:
            graph_id: Optional graph id to filter by.
            active_only: When True, only active instances are returned.

        Returns:
            A list of VFXGraphInstance objects matching the filters.
        """
        with self._lock:
            instances = list(self._instances.values())
        result: List[VFXGraphInstance] = []
        for inst in instances:
            if graph_id is not None and inst.graph_id != graph_id:
                continue
            if active_only and not inst.active:
                continue
            result.append(inst)
        return result

    def stop_instance(self, instance_id: str) -> bool:
        """Deactivate a running instance.

        The instance record is retained (so its history remains
        queryable) but its ``active`` flag is set to False.

        Args:
            instance_id: The unique identifier of the instance.

        Returns:
            True if the instance was deactivated, False if not found.
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return False
            instance.active = False
            self._record_event(
                VFXEventKind.GRAPH_ACTIVATED,
                payload={
                    "instance_id": instance_id,
                    "graph_id": instance.graph_id,
                    "active": False,
                },
            )
            return True

    # ------------------------------------------------------------------
    # Events, stats, status and snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[VFXGraphEvent]:
        """Return audit events limited to the most recent ``limit`` entries.

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of VFXGraphEvent objects ordered from oldest to newest.
        """
        with self._lock:
            events = list(self._events)
        if limit > 0:
            events = events[-limit:]
        return events

    def get_stats(self) -> VFXGraphStats:
        """Compute aggregate statistics from the current engine state.

        Returns:
            A VFXGraphStats describing the current store counts and
            per-status graph distribution.
        """
        with self._lock:
            total_nodes = sum(len(g.nodes) for g in self._graphs.values())
            total_connections = sum(
                len(g.connections) for g in self._graphs.values()
            )
            by_status: Dict[str, int] = {}
            for graph in self._graphs.values():
                key = graph.status.value
                by_status[key] = by_status.get(key, 0) + 1
            graph_count = len(self._graphs)
            avg_nodes = (total_nodes / graph_count) if graph_count else 0.0
            return VFXGraphStats(
                total_graphs=graph_count,
                total_instances=len(self._instances),
                total_nodes=total_nodes,
                total_connections=total_connections,
                graphs_by_status=by_status,
                avg_nodes_per_graph=avg_nodes,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current VFX graph engine state.

        The ``initialized`` flag is always the first key in the returned
        dictionary, followed by store counts and aggregate statistics.

        Returns:
            A dictionary with the system status.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_graphs": len(self._graphs),
                "total_instances": len(self._instances),
                "total_compile_results": len(self._compile_results),
                "total_events": len(self._events),
                "graph_counter": self._graph_counter,
                "node_counter": self._node_counter,
                "connection_counter": self._connection_counter,
                "parameter_counter": self._parameter_counter,
                "instance_counter": self._instance_counter,
                "compile_counter": self._compile_counter,
                "event_counter": self._event_counter,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> VFXGraphSnapshot:
        """Capture an immutable snapshot of the VFX graph engine state.

        Returns:
            A VFXGraphSnapshot capturing the system state at this moment.
        """
        with self._lock:
            stats = self.get_stats()
            return VFXGraphSnapshot(
                initialized=self._initialized,
                graphs=list(self._graphs.values()),
                instances=list(self._instances.values()),
                compile_results=list(self._compile_results.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data.

        Restores the engine to its initial state, including the seed
        graphs, parameters, instance and audit events.
        """
        with self._lock:
            self._graphs.clear()
            self._instances.clear()
            self._compile_results.clear()
            self._events.clear()
            self._graph_counter = 0
            self._node_counter = 0
            self._connection_counter = 0
            self._parameter_counter = 0
            self._instance_counter = 0
            self._compile_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_vfx_graph() -> VFXGraphEngine:
    """Return the singleton VFXGraphEngine instance."""
    return VFXGraphEngine.get_instance()
