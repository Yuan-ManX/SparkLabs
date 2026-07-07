"""
SparkLabs Engine - Cable Physics System

A verlet-integration-based cable and rope physics runtime for the SparkLabs
AI-native game engine. Cables are 1D chains of nodes connected by distance
constraints, complementing the 2D cloth physics and rigid body dynamics
modules. The system supports multiple cable types (rope, chain, vine, whip,
elastic), point-to-point and body attachments, tension computation with
break thresholds, gravity and wind influence, and sphere collision response.

Architecture:
  CablePhysicsSystem (singleton)
    |-- CableNode, CableDefinition, CableParams,
       CableStats, CableSnapshot, CableEvent
    |-- CableKind, CableEndpointType, CableEventKind

Core Capabilities:
  - register_cable / get_cable / list_cables / update_cable / remove_cable:
    cable lifecycle with verlet node chains and configurable parameters.
  - attach_endpoint / detach_endpoint: bind cable endpoints to fixed points
    or dynamic body references.
  - set_params: update stiffness, damping, gravity, wind, break threshold.
  - compute_tension: per-segment tension analysis with max and average.
  - step: verlet integration with constraint relaxation iterations.
  - find_collisions: sphere-vs-cable collision detection and response.
  - break_cable: force-break a cable at its highest-tension segment.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CablePhysicsSystem.get_instance` or the module-level
:func:`get_cable_physics` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CABLES: int = 2000
_MAX_NODES_PER_CABLE: int = 500
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


# Default cable parameters by kind
_DEFAULT_CABLE_PARAMS: Dict[str, Dict[str, Any]] = {
    "rope": {
        "stiffness": 0.8,
        "damping": 0.05,
        "gravity_scale": 1.0,
        "break_tension": 0.5,
        "max_stretch_ratio": 1.5,
        "iterations": 8,
    },
    "chain": {
        "stiffness": 0.95,
        "damping": 0.02,
        "gravity_scale": 1.2,
        "break_tension": 0.8,
        "max_stretch_ratio": 1.3,
        "iterations": 12,
    },
    "cable": {
        "stiffness": 0.9,
        "damping": 0.03,
        "gravity_scale": 0.8,
        "break_tension": 0.6,
        "max_stretch_ratio": 1.4,
        "iterations": 10,
    },
    "vine": {
        "stiffness": 0.5,
        "damping": 0.1,
        "gravity_scale": 1.0,
        "break_tension": 0.3,
        "max_stretch_ratio": 1.8,
        "iterations": 6,
    },
    "whip": {
        "stiffness": 0.7,
        "damping": 0.08,
        "gravity_scale": 0.6,
        "break_tension": 0.4,
        "max_stretch_ratio": 1.6,
        "iterations": 8,
    },
    "elastic": {
        "stiffness": 0.3,
        "damping": 0.15,
        "gravity_scale": 0.5,
        "break_tension": 2.0,
        "max_stretch_ratio": 3.0,
        "iterations": 4,
    },
}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class CableKind(Enum):
    """Cable material types affecting physics parameters."""
    ROPE = "rope"
    CHAIN = "chain"
    CABLE = "cable"
    VINE = "vine"
    WHIP = "whip"
    ELASTIC = "elastic"


class CableEndpointType(Enum):
    """Attachment mode for a cable endpoint."""
    FIXED = "fixed"
    FREE = "free"
    ATTACHED_BODY = "attached_body"
    ATTACHED_POINT = "attached_point"


class CableEventKind(Enum):
    """Audit event types emitted by the cable physics system."""
    CABLE_REGISTERED = "cable_registered"
    CABLE_REMOVED = "cable_removed"
    ENDPOINT_ATTACHED = "endpoint_attached"
    ENDPOINT_DETACHED = "endpoint_detached"
    PARAMS_UPDATED = "params_updated"
    TENSION_EXCEEDED = "tension_exceeded"
    CABLE_BROKEN = "cable_broken"
    NODE_COLLISION = "node_collision"
    STEP_COMPLETED = "step_completed"
    CABLE_RESET = "cable_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CableNode:
    """A single node in a verlet cable chain."""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    prev_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    pinned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CableParams:
    """Tunable physics parameters for a cable."""
    stiffness: float = 0.8
    damping: float = 0.05
    gravity_scale: float = 1.0
    wind_force: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    break_tension: float = 0.5
    max_stretch_ratio: float = 1.5
    iterations: int = 8

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CableDefinition:
    """A complete cable with verlet nodes and endpoint bindings."""
    cable_id: str = ""
    name: str = ""
    description: str = ""
    kind: str = CableKind.ROPE.value
    segment_count: int = 10
    segment_length: float = 0.5
    nodes: List[CableNode] = field(default_factory=list)
    endpoint_a_type: str = CableEndpointType.FIXED.value
    endpoint_a_ref: str = ""
    endpoint_a_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    endpoint_b_type: str = CableEndpointType.FIXED.value
    endpoint_b_ref: str = ""
    endpoint_b_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    params: CableParams = field(default_factory=CableParams)
    broken: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CableStats:
    """Aggregate statistics for the cable physics system."""
    total_cables: int = 0
    total_nodes: int = 0
    broken_cables: int = 0
    total_steps: int = 0
    total_breaks: int = 0
    total_collisions: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CableSnapshot:
    """Point-in-time snapshot of cable physics state."""
    total_cables: int = 0
    total_nodes: int = 0
    broken_cables: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CableEvent:
    """An audit event emitted by the cable physics system."""
    event_id: str = ""
    kind: str = CableEventKind.CABLE_REGISTERED.value
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# CablePhysicsSystem Singleton
# ---------------------------------------------------------------------------


class CablePhysicsSystem:
    """Verlet-integration cable physics with constraint relaxation.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["CablePhysicsSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._cables: Dict[str, CableDefinition] = {}
        self._events: List[CableEvent] = []
        self._stats = CableStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CablePhysicsSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed initial cables for demonstration and testing."""
        # Rope bridge: 10 segments spanning a chasm
        self._register_cable_internal(
            cable_id="cbl_rope_bridge",
            name="Rope Bridge",
            description="A rope cable spanning a chasm.",
            kind=CableKind.ROPE.value,
            segment_count=10,
            segment_length=0.8,
            start_point=(0.0, 3.0, 0.0),
            end_point=(8.0, 3.0, 0.0),
            endpoint_a_type=CableEndpointType.FIXED.value,
            endpoint_b_type=CableEndpointType.FIXED.value,
            params=CableParams(
                stiffness=0.8,
                damping=0.05,
                gravity_scale=1.0,
                break_tension=0.5,
                max_stretch_ratio=1.5,
                iterations=8,
            ),
        )

        # Chain chandelier: 5 segments hanging from ceiling
        self._register_cable_internal(
            cable_id="cbl_chandelier",
            name="Chandelier Chain",
            description="A chain supporting a chandelier.",
            kind=CableKind.CHAIN.value,
            segment_count=5,
            segment_length=0.4,
            start_point=(4.0, 5.0, 4.0),
            end_point=(4.0, 3.0, 4.0),
            endpoint_a_type=CableEndpointType.FIXED.value,
            endpoint_b_type=CableEndpointType.ATTACHED_BODY.value,
            endpoint_b_ref="body_chandelier",
            params=CableParams(
                stiffness=0.95,
                damping=0.02,
                gravity_scale=1.2,
                break_tension=0.8,
                max_stretch_ratio=1.3,
                iterations=12,
            ),
        )

        # Grappling rope: 8 segments, one end free
        self._register_cable_internal(
            cable_id="cbl_grappling",
            name="Grappling Rope",
            description="A grappling rope with a free end.",
            kind=CableKind.ROPE.value,
            segment_count=8,
            segment_length=0.6,
            start_point=(2.0, 4.0, 2.0),
            end_point=(2.0, 0.0, 2.0),
            endpoint_a_type=CableEndpointType.ATTACHED_BODY.value,
            endpoint_a_ref="actor_player_1",
            endpoint_b_type=CableEndpointType.FREE.value,
            params=CableParams(
                stiffness=0.75,
                damping=0.06,
                gravity_scale=1.0,
                break_tension=0.45,
                max_stretch_ratio=1.6,
                iterations=8,
            ),
        )
        self._initialized = True

    def _register_cable_internal(
        self,
        cable_id: str,
        name: str,
        description: str,
        kind: str,
        segment_count: int,
        segment_length: float,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
        endpoint_a_type: str = CableEndpointType.FIXED.value,
        endpoint_b_type: str = CableEndpointType.FIXED.value,
        endpoint_a_ref: str = "",
        endpoint_b_ref: str = "",
        params: Optional[CableParams] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CableDefinition:
        """Internal cable registration used by both public API and seeds."""
        seg_count = max(2, _safe_int(segment_count, 10))
        if seg_count > _MAX_NODES_PER_CABLE - 1:
            seg_count = _MAX_NODES_PER_CABLE - 1
        seg_len = max(0.01, _safe_float(segment_length, 0.5))
        nodes: List[CableNode] = []
        for i in range(seg_count + 1):
            t = i / seg_count
            px = start_point[0] + (end_point[0] - start_point[0]) * t
            py = start_point[1] + (end_point[1] - start_point[1]) * t
            pz = start_point[2] + (end_point[2] - start_point[2]) * t
            pinned = (
                (i == 0 and endpoint_a_type == CableEndpointType.FIXED.value)
                or (i == seg_count and endpoint_b_type == CableEndpointType.FIXED.value)
            )
            nodes.append(CableNode(
                position=(px, py, pz),
                prev_position=(px, py, pz),
                pinned=pinned,
            ))
        cable = CableDefinition(
            cable_id=cable_id,
            name=name,
            description=description,
            kind=kind,
            segment_count=seg_count,
            segment_length=seg_len,
            nodes=nodes,
            endpoint_a_type=endpoint_a_type,
            endpoint_a_ref=endpoint_a_ref,
            endpoint_a_position=tuple(start_point),
            endpoint_b_type=endpoint_b_type,
            endpoint_b_ref=endpoint_b_ref,
            endpoint_b_position=tuple(end_point),
            params=params or CableParams(),
            metadata=metadata or {},
        )
        self._cables[cable_id] = cable
        self._emit(
            CableEventKind.CABLE_REGISTERED.value,
            {"cable_id": cable_id, "kind": kind, "segments": seg_count},
        )
        return cable

    def _emit(self, kind: str, payload: Dict[str, Any]) -> None:
        event = CableEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            payload=payload,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Cable Lifecycle
    # ------------------------------------------------------------------

    def register_cable(
        self,
        cable_id: str,
        name: str = "",
        description: str = "",
        kind: str = CableKind.ROPE.value,
        segment_count: int = 10,
        segment_length: float = 0.5,
        start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        end_point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        endpoint_a_type: str = CableEndpointType.FIXED.value,
        endpoint_b_type: str = CableEndpointType.FIXED.value,
        endpoint_a_ref: str = "",
        endpoint_b_ref: str = "",
        params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CableDefinition:
        """Register a new cable with verlet nodes.

        Raises ValueError if cable_id already exists.
        """
        cid = str(cable_id).strip()
        if not cid:
            raise ValueError("cable_id must not be empty")
        if cid in self._cables:
            raise ValueError(f"cable_id already exists: {cid}")
        cable_params = CableParams()
        if params:
            cable_params.stiffness = _clamp(
                _safe_float(params.get("stiffness", 0.8), 0.8), 0.0, 1.0
            )
            cable_params.damping = _clamp(
                _safe_float(params.get("damping", 0.05), 0.05), 0.0, 1.0
            )
            cable_params.gravity_scale = _safe_float(
                params.get("gravity_scale", 1.0), 1.0
            )
            wind = params.get("wind_force", [0.0, 0.0, 0.0])
            if isinstance(wind, (list, tuple)) and len(wind) >= 3:
                cable_params.wind_force = (
                    _safe_float(wind[0]),
                    _safe_float(wind[1]),
                    _safe_float(wind[2]),
                )
            cable_params.break_tension = max(
                0.0, _safe_float(params.get("break_tension", 0.5), 0.5)
            )
            cable_params.max_stretch_ratio = max(
                1.0, _safe_float(params.get("max_stretch_ratio", 1.5), 1.5)
            )
            cable_params.iterations = max(
                1, _safe_int(params.get("iterations", 8), 8)
            )
        cable = self._register_cable_internal(
            cable_id=cid,
            name=name,
            description=description,
            kind=kind,
            segment_count=segment_count,
            segment_length=segment_length,
            start_point=tuple(start_point),
            end_point=tuple(end_point),
            endpoint_a_type=endpoint_a_type,
            endpoint_b_type=endpoint_b_type,
            endpoint_a_ref=endpoint_a_ref,
            endpoint_b_ref=endpoint_b_ref,
            params=cable_params,
            metadata=metadata,
        )
        _evict_fifo_dict(self._cables, _MAX_CABLES)
        return cable

    def get_cable(self, cable_id: str) -> Optional[CableDefinition]:
        return self._cables.get(str(cable_id).strip())

    def list_cables(
        self,
        kind: str = "",
        broken_only: bool = False,
        limit: int = 100,
    ) -> List[CableDefinition]:
        results: List[CableDefinition] = []
        for cable in self._cables.values():
            if kind and cable.kind != kind:
                continue
            if broken_only and not cable.broken:
                continue
            results.append(cable)
            if len(results) >= max(0, int(limit)):
                break
        return results

    def update_cable(
        self,
        cable_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CableDefinition]:
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return None
        if name is not None:
            cable.name = str(name)
        if description is not None:
            cable.description = str(description)
        if metadata is not None:
            cable.metadata = dict(metadata)
        return cable

    def remove_cable(self, cable_id: str) -> bool:
        cid = str(cable_id).strip()
        if cid not in self._cables:
            return False
        del self._cables[cid]
        self._emit(CableEventKind.CABLE_REMOVED.value, {"cable_id": cid})
        return True

    # ------------------------------------------------------------------
    # Endpoint Management
    # ------------------------------------------------------------------

    def attach_endpoint(
        self,
        cable_id: str,
        endpoint: str = "b",
        target_type: str = CableEndpointType.ATTACHED_POINT.value,
        target_ref: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> Dict[str, Any]:
        """Attach a cable endpoint to a fixed point or body reference.

        Returns dict with ok, cable_id, endpoint, target_type.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        ep = endpoint.lower()
        pos = tuple(position)
        if ep == "a":
            cable.endpoint_a_type = target_type
            cable.endpoint_a_ref = target_ref
            cable.endpoint_a_position = pos
            if cable.nodes and target_type == CableEndpointType.FIXED.value:
                cable.nodes[0].pinned = True
                cable.nodes[0].position = pos
                cable.nodes[0].prev_position = pos
        elif ep == "b":
            cable.endpoint_b_type = target_type
            cable.endpoint_b_ref = target_ref
            cable.endpoint_b_position = pos
            if cable.nodes and target_type == CableEndpointType.FIXED.value:
                cable.nodes[-1].pinned = True
                cable.nodes[-1].position = pos
                cable.nodes[-1].prev_position = pos
        else:
            return {"ok": False, "error": "endpoint must be 'a' or 'b'"}
        self._emit(
            CableEventKind.ENDPOINT_ATTACHED.value,
            {
                "cable_id": cable.cable_id,
                "endpoint": ep,
                "target_type": target_type,
                "target_ref": target_ref,
            },
        )
        return {
            "ok": True,
            "cable_id": cable.cable_id,
            "endpoint": ep,
            "target_type": target_type,
        }

    def detach_endpoint(self, cable_id: str, endpoint: str = "b") -> Dict[str, Any]:
        """Detach a cable endpoint, making it free.

        Returns dict with ok, cable_id, endpoint.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        ep = endpoint.lower()
        if ep == "a":
            cable.endpoint_a_type = CableEndpointType.FREE.value
            cable.endpoint_a_ref = ""
            if cable.nodes:
                cable.nodes[0].pinned = False
        elif ep == "b":
            cable.endpoint_b_type = CableEndpointType.FREE.value
            cable.endpoint_b_ref = ""
            if cable.nodes:
                cable.nodes[-1].pinned = False
        else:
            return {"ok": False, "error": "endpoint must be 'a' or 'b'"}
        self._emit(
            CableEventKind.ENDPOINT_DETACHED.value,
            {"cable_id": cable.cable_id, "endpoint": ep},
        )
        return {"ok": True, "cable_id": cable.cable_id, "endpoint": ep}

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    def set_params(
        self, cable_id: str, params: Dict[str, Any]
    ) -> Optional[CableDefinition]:
        """Update physics parameters for a cable."""
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return None
        if "stiffness" in params:
            cable.params.stiffness = _clamp(
                _safe_float(params["stiffness"], cable.params.stiffness), 0.0, 1.0
            )
        if "damping" in params:
            cable.params.damping = _clamp(
                _safe_float(params["damping"], cable.params.damping), 0.0, 1.0
            )
        if "gravity_scale" in params:
            cable.params.gravity_scale = _safe_float(
                params["gravity_scale"], cable.params.gravity_scale
            )
        if "wind_force" in params:
            wind = params["wind_force"]
            if isinstance(wind, (list, tuple)) and len(wind) >= 3:
                cable.params.wind_force = (
                    _safe_float(wind[0]),
                    _safe_float(wind[1]),
                    _safe_float(wind[2]),
                )
        if "break_tension" in params:
            cable.params.break_tension = max(
                0.0, _safe_float(params["break_tension"], cable.params.break_tension)
            )
        if "max_stretch_ratio" in params:
            cable.params.max_stretch_ratio = max(
                1.0,
                _safe_float(
                    params["max_stretch_ratio"], cable.params.max_stretch_ratio
                ),
            )
        if "iterations" in params:
            cable.params.iterations = max(
                1, _safe_int(params["iterations"], cable.params.iterations)
            )
        self._emit(
            CableEventKind.PARAMS_UPDATED.value,
            {"cable_id": cable.cable_id},
        )
        return cable

    # ------------------------------------------------------------------
    # Tension and Simulation
    # ------------------------------------------------------------------

    def compute_tension(self, cable_id: str) -> Dict[str, Any]:
        """Compute per-segment tension for a cable.

        Returns dict with ok, cable_id, max_tension, avg_tension, segments.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        segments: List[Dict[str, Any]] = []
        tensions: List[float] = []
        for i in range(len(cable.nodes) - 1):
            n1 = cable.nodes[i]
            n2 = cable.nodes[i + 1]
            dx = n2.position[0] - n1.position[0]
            dy = n2.position[1] - n1.position[1]
            dz = n2.position[2] - n1.position[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if cable.segment_length > 0:
                tension = max(
                    0.0, (dist - cable.segment_length) / cable.segment_length
                )
            else:
                tension = 0.0
            tensions.append(tension)
            segments.append({
                "index": i,
                "length": round(dist, 6),
                "tension": round(tension, 6),
            })
        max_tension = max(tensions) if tensions else 0.0
        avg_tension = sum(tensions) / len(tensions) if tensions else 0.0
        if max_tension > cable.params.break_tension and not cable.broken:
            cable.broken = True
            self._stats.total_breaks += 1
            self._emit(
                CableEventKind.TENSION_EXCEEDED.value,
                {
                    "cable_id": cable.cable_id,
                    "max_tension": max_tension,
                    "break_tension": cable.params.break_tension,
                },
            )
        return {
            "ok": True,
            "cable_id": cable.cable_id,
            "max_tension": round(max_tension, 6),
            "avg_tension": round(avg_tension, 6),
            "segment_count": len(segments),
            "segments": segments,
            "broken": cable.broken,
        }

    def step(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance verlet integration for all cables by dt seconds.

        Returns dict with ok, stepped_count, broken_count, dt.
        """
        step_dt = max(0.0001, _safe_float(dt, 0.016))
        stepped = 0
        broken_now = 0
        gravity = -9.81
        for cable in self._cables.values():
            if cable.broken:
                continue
            p = cable.params
            dt_sq = step_dt * step_dt
            # Verlet integration for non-pinned nodes
            for node in cable.nodes:
                if node.pinned:
                    node.prev_position = node.position
                    continue
                vx = (node.position[0] - node.prev_position[0]) * (
                    1.0 - p.damping
                )
                vy = (node.position[1] - node.prev_position[1]) * (
                    1.0 - p.damping
                )
                vz = (node.position[2] - node.prev_position[2]) * (
                    1.0 - p.damping
                )
                node.prev_position = node.position
                new_x = node.position[0] + vx + p.wind_force[0] * dt_sq
                new_y = (
                    node.position[1]
                    + vy
                    + gravity * p.gravity_scale * dt_sq
                    + p.wind_force[1] * dt_sq
                )
                new_z = node.position[2] + vz + p.wind_force[2] * dt_sq
                node.position = (new_x, new_y, new_z)
            # Constraint relaxation
            iterations = max(1, p.iterations)
            for _ in range(iterations):
                for i in range(len(cable.nodes) - 1):
                    n1 = cable.nodes[i]
                    n2 = cable.nodes[i + 1]
                    dx = n2.position[0] - n1.position[0]
                    dy = n2.position[1] - n1.position[1]
                    dz = n2.position[2] - n1.position[2]
                    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                    if dist < 1e-9:
                        continue
                    target = cable.segment_length
                    stretch = dist / target if target > 0 else 1.0
                    if stretch > p.max_stretch_ratio:
                        cable.broken = True
                        broken_now += 1
                        self._emit(
                            CableEventKind.CABLE_BROKEN.value,
                            {
                                "cable_id": cable.cable_id,
                                "segment": i,
                                "stretch": round(stretch, 6),
                            },
                        )
                        break
                    diff = (dist - target) / dist
                    factor = p.stiffness * 0.5 * diff
                    if not n1.pinned:
                        n1.position = (
                            n1.position[0] + dx * factor,
                            n1.position[1] + dy * factor,
                            n1.position[2] + dz * factor,
                        )
                    if not n2.pinned:
                        n2.position = (
                            n2.position[0] - dx * factor,
                            n2.position[1] - dy * factor,
                            n2.position[2] - dz * factor,
                        )
                if cable.broken:
                    break
            stepped += 1
        self._stats.total_steps += 1
        self._stats.total_breaks += broken_now
        self._emit(
            CableEventKind.STEP_COMPLETED.value,
            {"dt": step_dt, "stepped": stepped, "broken": broken_now},
        )
        return {
            "ok": True,
            "stepped_count": stepped,
            "broken_count": broken_now,
            "dt": step_dt,
        }

    def find_collisions(
        self,
        cable_id: str,
        sphere_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        sphere_radius: float = 0.5,
    ) -> Dict[str, Any]:
        """Find cable nodes colliding with a sphere and push them out.

        Returns dict with ok, cable_id, collisions, collision_count.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        sp = tuple(sphere_position)
        sr = max(0.0, _safe_float(sphere_radius, 0.5))
        collisions: List[Dict[str, Any]] = []
        for i, node in enumerate(cable.nodes):
            dx = node.position[0] - sp[0]
            dy = node.position[1] - sp[1]
            dz = node.position[2] - sp[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < sr:
                # Push node out of sphere surface
                if dist > 1e-9 and not node.pinned:
                    push = (sr - dist) / dist
                    node.position = (
                        node.position[0] + dx * push,
                        node.position[1] + dy * push,
                        node.position[2] + dz * push,
                    )
                collisions.append({
                    "node_index": i,
                    "distance": round(dist, 6),
                    "penetration": round(max(0.0, sr - dist), 6),
                })
        if collisions:
            self._stats.total_collisions += len(collisions)
            self._emit(
                CableEventKind.NODE_COLLISION.value,
                {
                    "cable_id": cable.cable_id,
                    "collision_count": len(collisions),
                },
            )
        return {
            "ok": True,
            "cable_id": cable.cable_id,
            "collisions": collisions,
            "collision_count": len(collisions),
        }

    def break_cable(self, cable_id: str) -> Dict[str, Any]:
        """Force-break a cable at its highest-tension segment.

        Returns dict with ok, cable_id, broken_segment, tension_at_break.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        if cable.broken:
            return {"ok": True, "cable_id": cable.cable_id, "already_broken": True}
        # Find highest-tension segment
        worst_index = 0
        worst_tension = -1.0
        for i in range(len(cable.nodes) - 1):
            n1 = cable.nodes[i]
            n2 = cable.nodes[i + 1]
            dx = n2.position[0] - n1.position[0]
            dy = n2.position[1] - n1.position[1]
            dz = n2.position[2] - n1.position[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if cable.segment_length > 0:
                tension = max(
                    0.0,
                    (dist - cable.segment_length) / cable.segment_length,
                )
            else:
                tension = 0.0
            if tension > worst_tension:
                worst_tension = tension
                worst_index = i
        cable.broken = True
        self._stats.total_breaks += 1
        self._emit(
            CableEventKind.CABLE_BROKEN.value,
            {
                "cable_id": cable.cable_id,
                "segment": worst_index,
                "tension": round(worst_tension, 6),
                "forced": True,
            },
        )
        return {
            "ok": True,
            "cable_id": cable.cable_id,
            "broken_segment": worst_index,
            "tension_at_break": round(worst_tension, 6),
        }

    # ------------------------------------------------------------------
    # Node Access
    # ------------------------------------------------------------------

    def get_nodes(self, cable_id: str) -> Dict[str, Any]:
        """Return the node positions for a cable.

        Returns dict with ok, cable_id, nodes, node_count.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        nodes_data = [
            {
                "index": i,
                "position": list(node.position),
                "pinned": node.pinned,
            }
            for i, node in enumerate(cable.nodes)
        ]
        return {
            "ok": True,
            "cable_id": cable.cable_id,
            "nodes": nodes_data,
            "node_count": len(nodes_data),
        }

    def pin_node(self, cable_id: str, node_index: int) -> Dict[str, Any]:
        """Pin a specific node so it does not move during integration.

        Returns dict with ok, cable_id, node_index, pinned.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        idx = _safe_int(node_index, -1)
        if idx < 0 or idx >= len(cable.nodes):
            return {"ok": False, "error": "node_index out of range"}
        cable.nodes[idx].pinned = True
        return {
            "ok": True,
            "cable_id": cable.cable_id,
            "node_index": idx,
            "pinned": True,
        }

    def unpin_node(self, cable_id: str, node_index: int) -> Dict[str, Any]:
        """Unpin a specific node so it moves freely during integration.

        Returns dict with ok, cable_id, node_index, pinned.
        """
        cable = self._cables.get(str(cable_id).strip())
        if cable is None:
            return {"ok": False, "error": "cable not found"}
        idx = _safe_int(node_index, -1)
        if idx < 0 or idx >= len(cable.nodes):
            return {"ok": False, "error": "node_index out of range"}
        cable.nodes[idx].pinned = False
        return {
            "ok": True,
            "cable_id": cable.cable_id,
            "node_index": idx,
            "pinned": False,
        }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: str = "", limit: int = 50) -> List[CableEvent]:
        results: List[CableEvent] = []
        for event in reversed(self._events):
            if kind and event.kind != kind:
                continue
            results.append(event)
            if len(results) >= max(0, int(limit)):
                break
        return results

    def get_stats(self) -> CableStats:
        self._stats.total_cables = len(self._cables)
        self._stats.total_nodes = sum(len(c.nodes) for c in self._cables.values())
        self._stats.broken_cables = sum(
            1 for c in self._cables.values() if c.broken
        )
        self._stats.timestamp = _now()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "cables": len(self._cables),
            "nodes": sum(len(c.nodes) for c in self._cables.values()),
            "broken": sum(1 for c in self._cables.values() if c.broken),
            "events": len(self._events),
        }

    def get_snapshot(self) -> CableSnapshot:
        return CableSnapshot(
            total_cables=len(self._cables),
            total_nodes=sum(len(c.nodes) for c in self._cables.values()),
            broken_cables=sum(1 for c in self._cables.values() if c.broken),
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._init_lock:
            self._cables.clear()
            self._events.clear()
            self._stats = CableStats()
            self._seed()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_cable_physics() -> CablePhysicsSystem:
    """Get the singleton CablePhysicsSystem instance."""
    return CablePhysicsSystem.get_instance()
