"""
SparkLabs Engine - Live Tuning

Unified surface for live-tuning engine parameters at runtime. Parameters
are organized by subsystem, have type constraints (min/max/enum values),
and can be saved into named profiles that can be applied instantly.

The tuning surface enables AI agents to adjust engine behavior in
real-time without restart. When a parameter changes, registered watchers
are notified with the old and new values, allowing dependent systems to
react dynamically. All changes are logged for audit and rollback.

Parameter types supported: INTEGER, FLOAT, BOOLEAN, STRING, ENUM.
Profiles capture snapshots of parameter values and can be applied,
diffed, and exported for persistence.

Architecture:
  LiveTuningEngine (singleton)
    |-- TunableParameter (a single registered parameter with constraints)
    |-- ParameterValue (a name/subsystem/value/applied-at tuple)
    |-- TuningProfile (a named preset capturing parameter values)
    |-- ParameterChange (an audit-log entry for a parameter modification)
    |-- ParameterWatcher (a callback subscription for parameter changes)
    |-- TuningDiff (a single difference between current and profile values)
    |-- TuningSnapshot (an aggregate snapshot of engine state)
    |-- ParameterType / ChangeKind / ValidationResult (domain enums)
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

_datetime = datetime.datetime


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ParameterType(Enum):
    """The set of value types a tunable parameter may hold."""

    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    ENUM = "enum"


class ChangeKind(Enum):
    """The kind of operation that produced a change-log entry."""

    SET = "set"
    RESET_TO_DEFAULT = "reset_to_default"
    PROFILE_APPLIED = "profile_applied"
    PROFILE_SAVED = "profile_saved"
    PARAMETER_REGISTERED = "parameter_registered"
    PARAMETER_REMOVED = "parameter_removed"


class ValidationResult(Enum):
    """The outcome of validating a value against a parameter's constraints."""

    VALID = "valid"
    INVALID_TYPE = "invalid_type"
    OUT_OF_RANGE = "out_of_range"
    INVALID_ENUM_VALUE = "invalid_enum_value"
    UNKNOWN_PARAMETER = "unknown_parameter"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TunableParameter:
    """A single registered parameter with type and range constraints.

    Attributes:
        name: Local name of the parameter within its subsystem.
        subsystem: The engine subsystem that owns the parameter.
        description: Human-readable description of the parameter.
        param_type: The value type (INTEGER, FLOAT, BOOLEAN, STRING, ENUM).
        default_value: The value the parameter reverts to on reset.
        min_value: Optional inclusive lower bound for numeric parameters.
        max_value: Optional inclusive upper bound for numeric parameters.
        enum_values: Optional list of allowed values for ENUM parameters.
        current_value: The live value of the parameter.
        tags: Free-form tags used for grouping and filtering.
        registered_at: ISO timestamp of registration.
        updated_at: ISO timestamp of the most recent value change.
    """

    name: str
    subsystem: str
    description: str
    param_type: ParameterType
    default_value: Any
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    enum_values: Optional[List[Any]] = None
    current_value: Any = None
    tags: List[str] = field(default_factory=list)
    registered_at: str = field(default_factory=lambda: _datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: _datetime.utcnow().isoformat())

    @property
    def qualified_name(self) -> str:
        """The globally unique identifier ``"{subsystem}.{name}"``."""
        return f"{self.subsystem}.{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "subsystem": self.subsystem,
            "description": self.description,
            "param_type": self.param_type.value,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "enum_values": list(self.enum_values) if self.enum_values is not None else None,
            "current_value": self.current_value,
            "tags": list(self.tags),
            "registered_at": self.registered_at,
            "updated_at": self.updated_at,
            "qualified_name": self.qualified_name,
        }


@dataclass
class ParameterValue:
    """A single parameter value with the moment it was applied.

    Attributes:
        name: Local name of the parameter.
        subsystem: Subsystem that owns the parameter.
        value: The value that was applied.
        applied_at: ISO timestamp of application.
    """

    name: str
    subsystem: str
    value: Any
    applied_at: str = field(default_factory=lambda: _datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "subsystem": self.subsystem,
            "value": self.value,
            "applied_at": self.applied_at,
        }


@dataclass
class TuningProfile:
    """A named preset capturing a set of parameter values.

    Attributes:
        id: Unique identifier of the profile.
        name: Human-readable name of the profile.
        description: Human-readable description of the profile.
        values: Mapping of qualified name to captured value.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of the most recent update.
        tags: Free-form tags used for grouping and filtering.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    values: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: _datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: _datetime.utcnow().isoformat())
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "values": dict(self.values),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": list(self.tags),
        }


@dataclass
class ParameterChange:
    """A single audit-log entry describing a parameter modification.

    Attributes:
        id: Unique identifier of the change entry.
        parameter_name: Local name of the parameter that changed.
        subsystem: Subsystem that owns the parameter.
        old_value: The value before the change.
        new_value: The value after the change.
        kind: The kind of operation that produced the change.
        timestamp: ISO timestamp of the change.
        source: Identifier of the actor that produced the change.
        profile_id: Optional profile identifier when kind is PROFILE_APPLIED.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parameter_name: str = ""
    subsystem: str = ""
    old_value: Any = None
    new_value: Any = None
    kind: ChangeKind = ChangeKind.SET
    timestamp: str = field(default_factory=lambda: _datetime.utcnow().isoformat())
    source: str = "api"
    profile_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parameter_name": self.parameter_name,
            "subsystem": self.subsystem,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "profile_id": self.profile_id,
        }


@dataclass
class ParameterWatcher:
    """A callback subscription for parameter changes.

    Attributes:
        id: Unique identifier of the watcher.
        parameter_name: The parameter name to observe, or ``"*"`` for all.
        callback: The callable invoked with a ``ParameterChange`` on updates.
        active: Whether the watcher currently receives notifications.
        created_at: ISO timestamp of creation.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parameter_name: str = "*"
    callback: Optional[Callable[[ParameterChange], None]] = field(default=None, repr=False)
    active: bool = True
    created_at: str = field(default_factory=lambda: _datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parameter_name": self.parameter_name,
            "callback": str(self.callback),
            "active": self.active,
            "created_at": self.created_at,
        }


@dataclass
class TuningDiff:
    """A single difference between a current value and a profile value.

    Attributes:
        parameter_name: Local name of the parameter.
        subsystem: Subsystem that owns the parameter.
        current_value: The live value of the parameter.
        profile_value: The value recorded in the profile.
        difference: ``profile_value - current_value`` for numeric values,
            otherwise ``None``.
    """

    parameter_name: str
    subsystem: str
    current_value: Any
    profile_value: Any
    difference: Optional[Union[int, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "subsystem": self.subsystem,
            "current_value": self.current_value,
            "profile_value": self.profile_value,
            "difference": self.difference,
        }


@dataclass
class TuningSnapshot:
    """An aggregate snapshot of the tuning engine state.

    Attributes:
        parameter_count: Number of registered parameters.
        profile_count: Number of saved profiles.
        watcher_count: Number of registered watchers.
        change_count: Number of logged changes.
        subsystems: Sorted list of subsystem names.
        stats: Mapping of operational statistic names to values.
        timestamp: ISO timestamp of the snapshot.
    """

    parameter_count: int = 0
    profile_count: int = 0
    watcher_count: int = 0
    change_count: int = 0
    subsystems: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: _datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_count": self.parameter_count,
            "profile_count": self.profile_count,
            "watcher_count": self.watcher_count,
            "change_count": self.change_count,
            "subsystems": list(self.subsystems),
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Seed Parameter Definitions
# ---------------------------------------------------------------------------

# Each entry registers a default parameter at engine initialization. The
# values are kept as plain dictionaries so the seed loader stays declarative.
_SEED_PARAMETERS: List[Dict[str, Any]] = [
    # physics
    {
        "name": "gravity",
        "subsystem": "physics",
        "param_type": ParameterType.FLOAT,
        "default_value": -9.8,
        "description": "Downward acceleration applied to dynamic bodies.",
        "min_value": -100.0,
        "max_value": 100.0,
    },
    {
        "name": "time_scale",
        "subsystem": "physics",
        "param_type": ParameterType.FLOAT,
        "default_value": 1.0,
        "description": "Multiplier applied to simulation time progression.",
        "min_value": 0.0,
        "max_value": 10.0,
    },
    {
        "name": "fixed_timestep",
        "subsystem": "physics",
        "param_type": ParameterType.FLOAT,
        "default_value": 0.016,
        "description": "Fixed delta time used by the physics integrator.",
        "min_value": 0.001,
        "max_value": 0.1,
    },
    # rendering
    {
        "name": "vsync",
        "subsystem": "rendering",
        "param_type": ParameterType.BOOLEAN,
        "default_value": True,
        "description": "Synchronize frame presentation to the display refresh.",
    },
    {
        "name": "max_fps",
        "subsystem": "rendering",
        "param_type": ParameterType.INTEGER,
        "default_value": 60,
        "description": "Upper bound on frames presented per second.",
        "min_value": 15,
        "max_value": 240,
    },
    {
        "name": "shadow_quality",
        "subsystem": "rendering",
        "param_type": ParameterType.ENUM,
        "default_value": "high",
        "description": "Resolution and filtering quality of shadow maps.",
        "enum_values": ["low", "medium", "high", "ultra"],
    },
    {
        "name": "texture_filtering",
        "subsystem": "rendering",
        "param_type": ParameterType.ENUM,
        "default_value": "anisotropic",
        "description": "Sampling filter applied to textures.",
        "enum_values": ["nearest", "linear", "anisotropic"],
    },
    # audio
    {
        "name": "master_volume",
        "subsystem": "audio",
        "param_type": ParameterType.FLOAT,
        "default_value": 0.8,
        "description": "Linear gain applied to the master mix bus.",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    {
        "name": "music_volume",
        "subsystem": "audio",
        "param_type": ParameterType.FLOAT,
        "default_value": 0.7,
        "description": "Linear gain applied to the music bus.",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    {
        "name": "sfx_volume",
        "subsystem": "audio",
        "param_type": ParameterType.FLOAT,
        "default_value": 0.9,
        "description": "Linear gain applied to the sound effects bus.",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    # gameplay
    {
        "name": "difficulty",
        "subsystem": "gameplay",
        "param_type": ParameterType.ENUM,
        "default_value": "normal",
        "description": "Global difficulty tier applied to gameplay logic.",
        "enum_values": ["easy", "normal", "hard", "nightmare"],
    },
    {
        "name": "player_speed",
        "subsystem": "gameplay",
        "param_type": ParameterType.FLOAT,
        "default_value": 5.0,
        "description": "Base movement speed of the player character.",
        "min_value": 0.1,
        "max_value": 50.0,
    },
    {
        "name": "enemy_aggression",
        "subsystem": "gameplay",
        "param_type": ParameterType.FLOAT,
        "default_value": 0.5,
        "description": "Aggression coefficient applied to enemy decision making.",
        "min_value": 0.0,
        "max_value": 1.0,
    },
    # ai
    {
        "name": "think_interval",
        "subsystem": "ai",
        "param_type": ParameterType.FLOAT,
        "default_value": 0.1,
        "description": "Interval between agent decision ticks in seconds.",
        "min_value": 0.01,
        "max_value": 1.0,
    },
    {
        "name": "max_agents",
        "subsystem": "ai",
        "param_type": ParameterType.INTEGER,
        "default_value": 100,
        "description": "Maximum number of active AI agents.",
        "min_value": 1,
        "max_value": 1000,
    },
]


# ---------------------------------------------------------------------------
# Live Tuning Engine (singleton)
# ---------------------------------------------------------------------------


class LiveTuningEngine:
    """
    Unified surface for live-tuning engine parameters at runtime.

    Parameters are organized by subsystem, validated against type and range
    constraints, and observable through watcher subscriptions. Named
    profiles capture snapshots of parameter values that can be applied,
    diffed, and exported for persistence. All modifications are recorded
    in a bounded change log for audit and rollback.

    Usage:
        engine = LiveTuningEngine.get_instance()
        engine.set_value("gravity", "physics", -20.0, source="agent")
        profile = engine.save_profile("low_gravity", "Low gravity preset")
    """

    _instance: Optional["LiveTuningEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._parameters: Dict[str, TunableParameter] = {}
        self._profiles: Dict[str, TuningProfile] = {}
        self._watchers: Dict[str, ParameterWatcher] = {}
        self._changes: List[ParameterChange] = []
        self._max_changes: int = 1000

        # Operational statistics
        self._total_sets: int = 0
        self._total_resets: int = 0
        self._total_profile_applies: int = 0
        self._total_profile_saves: int = 0
        self._total_validation_failures: int = 0
        self._last_change_at: str = ""

        self._initialized: bool = True

        self._initialize_seed_parameters()

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LiveTuningEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(name: str, subsystem: str) -> str:
        return f"{subsystem}.{name}"

    def _get_parameter_internal(
        self, name: str, subsystem: str
    ) -> Optional[TunableParameter]:
        return self._parameters.get(self._make_key(name, subsystem))

    def _initialize_seed_parameters(self) -> None:
        for definition in _SEED_PARAMETERS:
            self.register_parameter(
                name=definition["name"],
                subsystem=definition["subsystem"],
                param_type=definition["param_type"],
                default_value=definition["default_value"],
                description=definition.get("description", ""),
                min_value=definition.get("min_value"),
                max_value=definition.get("max_value"),
                enum_values=definition.get("enum_values"),
                tags=definition.get("tags"),
            )

    def _coerce_value(self, param: TunableParameter, value: Any) -> Any:
        """Coerce a validated value into the parameter's canonical type."""
        if param.param_type == ParameterType.INTEGER:
            if isinstance(value, bool):
                return value
            if isinstance(value, float):
                return int(value)
            return value
        if param.param_type == ParameterType.FLOAT:
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return float(value)
            return value
        return value

    def _notify_watchers(self, change: ParameterChange) -> None:
        """Invoke watcher callbacks matching a change.

        Callbacks are invoked synchronously. Exceptions raised by individual
        callbacks are swallowed so that a faulty subscriber cannot break the
        tuning engine. Iteration uses a snapshot copy so that callbacks may
        safely register or remove watchers without corrupting the loop.
        """
        watchers = list(self._watchers.values())
        for watcher in watchers:
            if not watcher.active:
                continue
            if watcher.parameter_name == "*" or watcher.parameter_name == change.parameter_name:
                try:
                    watcher.callback(change)
                except Exception:
                    # A faulty subscriber must not abort the change pipeline.
                    pass

    def _commit_change(
        self,
        param: TunableParameter,
        new_value: Any,
        kind: ChangeKind,
        source: str,
        profile_id: Optional[str] = None,
    ) -> ParameterChange:
        """Apply a value to a parameter and record the change."""
        old_value = param.current_value
        param.current_value = new_value
        param.updated_at = _datetime.utcnow().isoformat()

        change = ParameterChange(
            id=uuid.uuid4().hex,
            parameter_name=param.name,
            subsystem=param.subsystem,
            old_value=old_value,
            new_value=new_value,
            kind=kind,
            timestamp=_datetime.utcnow().isoformat(),
            source=source,
            profile_id=profile_id,
        )

        self._changes.append(change)
        if len(self._changes) > self._max_changes:
            # Evict the oldest entries to keep the log bounded.
            del self._changes[: len(self._changes) - self._max_changes]

        self._last_change_at = change.timestamp
        if kind == ChangeKind.SET:
            self._total_sets += 1
        elif kind == ChangeKind.RESET_TO_DEFAULT:
            self._total_resets += 1
        elif kind == ChangeKind.PROFILE_APPLIED:
            self._total_profile_applies += 1

        self._notify_watchers(change)
        return change

    # ------------------------------------------------------------------
    # Parameter registration
    # ------------------------------------------------------------------

    def register_parameter(
        self,
        name: str,
        subsystem: str,
        param_type: ParameterType,
        default_value: Any,
        description: str = "",
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        enum_values: Optional[List[Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> TunableParameter:
        """Register a new tunable parameter.

        Raises:
            ValueError: If a parameter with the same name already exists in
                the given subsystem.
        """
        with self._lock:
            key = self._make_key(name, subsystem)
            if key in self._parameters:
                raise ValueError(
                    f"Parameter '{key}' is already registered"
                )

            param = TunableParameter(
                name=name,
                subsystem=subsystem,
                description=description,
                param_type=param_type,
                default_value=default_value,
                min_value=min_value,
                max_value=max_value,
                enum_values=list(enum_values) if enum_values is not None else None,
                current_value=default_value,
                tags=list(tags) if tags is not None else [],
            )
            self._parameters[key] = param
            return param

    def remove_parameter(self, name: str, subsystem: str) -> bool:
        """Remove a registered parameter. Returns True if removed."""
        with self._lock:
            key = self._make_key(name, subsystem)
            if key not in self._parameters:
                return False
            del self._parameters[key]
            return True

    def get_parameter(
        self, name: str, subsystem: str
    ) -> Optional[TunableParameter]:
        """Return a parameter by name and subsystem, or None if absent."""
        with self._lock:
            return self._get_parameter_internal(name, subsystem)

    def get_parameter_by_qualified_name(
        self, qualified_name: str
    ) -> Optional[TunableParameter]:
        """Return a parameter by its ``"subsystem.name"`` identifier."""
        with self._lock:
            return self._parameters.get(qualified_name)

    def list_parameters(
        self,
        subsystem: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[TunableParameter]:
        """List parameters, optionally filtered by subsystem and/or tag."""
        with self._lock:
            results: List[TunableParameter] = []
            for param in self._parameters.values():
                if subsystem is not None and param.subsystem != subsystem:
                    continue
                if tag is not None and tag not in param.tags:
                    continue
                results.append(param)
            return results

    def list_subsystems(self) -> List[str]:
        """Return a sorted list of subsystem names that own parameters."""
        with self._lock:
            return sorted({param.subsystem for param in self._parameters.values()})

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_value(
        self, name: str, subsystem: str, value: Any
    ) -> ValidationResult:
        """Validate a value against a parameter's constraints."""
        with self._lock:
            param = self._get_parameter_internal(name, subsystem)
            if param is None:
                return ValidationResult.UNKNOWN_PARAMETER

            if param.param_type == ParameterType.INTEGER:
                if isinstance(value, bool):
                    return ValidationResult.INVALID_TYPE
                if isinstance(value, int):
                    numeric = value
                elif isinstance(value, float) and value == int(value):
                    numeric = int(value)
                else:
                    return ValidationResult.INVALID_TYPE
                if param.min_value is not None and numeric < param.min_value:
                    return ValidationResult.OUT_OF_RANGE
                if param.max_value is not None and numeric > param.max_value:
                    return ValidationResult.OUT_OF_RANGE
                return ValidationResult.VALID

            if param.param_type == ParameterType.FLOAT:
                if isinstance(value, bool):
                    return ValidationResult.INVALID_TYPE
                if isinstance(value, (int, float)):
                    numeric = float(value)
                else:
                    return ValidationResult.INVALID_TYPE
                if param.min_value is not None and numeric < param.min_value:
                    return ValidationResult.OUT_OF_RANGE
                if param.max_value is not None and numeric > param.max_value:
                    return ValidationResult.OUT_OF_RANGE
                return ValidationResult.VALID

            if param.param_type == ParameterType.BOOLEAN:
                if isinstance(value, bool):
                    return ValidationResult.VALID
                return ValidationResult.INVALID_TYPE

            if param.param_type == ParameterType.STRING:
                if isinstance(value, str):
                    return ValidationResult.VALID
                return ValidationResult.INVALID_TYPE

            if param.param_type == ParameterType.ENUM:
                allowed = param.enum_values or []
                if value in allowed:
                    return ValidationResult.VALID
                return ValidationResult.INVALID_ENUM_VALUE

            return ValidationResult.INVALID_TYPE

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------

    def get_value(self, name: str, subsystem: str) -> Optional[Any]:
        """Return the current value of a parameter, or None if absent."""
        with self._lock:
            param = self._get_parameter_internal(name, subsystem)
            if param is None:
                return None
            return param.current_value

    def get_value_qualified(self, qualified_name: str) -> Optional[Any]:
        """Return the current value of a parameter by qualified name."""
        with self._lock:
            param = self._parameters.get(qualified_name)
            if param is None:
                return None
            return param.current_value

    def set_value(
        self,
        name: str,
        subsystem: str,
        value: Any,
        source: str = "api",
    ) -> ParameterChange:
        """Set a parameter value after validation.

        Raises:
            ValueError: If the parameter is unknown or the value fails
                validation.
        """
        with self._lock:
            param = self._get_parameter_internal(name, subsystem)
            if param is None:
                self._total_validation_failures += 1
                raise ValueError(
                    f"Unknown parameter '{self._make_key(name, subsystem)}'"
                )

            result = self.validate_value(name, subsystem, value)
            if result != ValidationResult.VALID:
                self._total_validation_failures += 1
                raise ValueError(
                    f"Validation failed for '{param.qualified_name}': {result.value}"
                )

            coerced = self._coerce_value(param, value)
            return self._commit_change(
                param, coerced, ChangeKind.SET, source
            )

    def set_value_qualified(
        self,
        qualified_name: str,
        value: Any,
        source: str = "api",
    ) -> ParameterChange:
        """Set a parameter value by its ``"subsystem.name"`` identifier.

        Raises:
            ValueError: If the qualified name is malformed or the parameter
                is unknown.
        """
        if "." not in qualified_name:
            raise ValueError(
                f"Qualified name must be 'subsystem.name', got '{qualified_name}'"
            )
        subsystem, name = qualified_name.split(".", 1)
        return self.set_value(name, subsystem, value, source=source)

    # ------------------------------------------------------------------
    # Reset operations
    # ------------------------------------------------------------------

    def reset_parameter(
        self, name: str, subsystem: str, source: str = "api"
    ) -> ParameterChange:
        """Reset a parameter to its default value.

        Raises:
            ValueError: If the parameter is unknown.
        """
        with self._lock:
            param = self._get_parameter_internal(name, subsystem)
            if param is None:
                raise ValueError(
                    f"Unknown parameter '{self._make_key(name, subsystem)}'"
                )
            default = self._coerce_value(param, param.default_value)
            return self._commit_change(
                param, default, ChangeKind.RESET_TO_DEFAULT, source
            )

    def reset_subsystem(
        self, subsystem: str, source: str = "api"
    ) -> List[ParameterChange]:
        """Reset all parameters within a subsystem to their defaults."""
        with self._lock:
            changes: List[ParameterChange] = []
            for param in self._parameters.values():
                if param.subsystem != subsystem:
                    continue
                default = self._coerce_value(param, param.default_value)
                change = self._commit_change(
                    param, default, ChangeKind.RESET_TO_DEFAULT, source
                )
                changes.append(change)
            return changes

    def reset_all(self, source: str = "api") -> List[ParameterChange]:
        """Reset every registered parameter to its default value."""
        with self._lock:
            changes: List[ParameterChange] = []
            for param in self._parameters.values():
                default = self._coerce_value(param, param.default_value)
                change = self._commit_change(
                    param, default, ChangeKind.RESET_TO_DEFAULT, source
                )
                changes.append(change)
            return changes

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def set_values_bulk(
        self,
        changes: List[Dict[str, Any]],
        source: str = "api",
    ) -> List[ParameterChange]:
        """Apply multiple parameter values at once.

        Each entry in ``changes`` is a mapping with the keys ``name``,
        ``subsystem`` and ``value``. Entries that fail validation are
        skipped (and counted as validation failures) without aborting the
        remaining entries. Returns the list of changes that were applied.
        """
        applied: List[ParameterChange] = []
        with self._lock:
            for entry in changes:
                name = entry.get("name")
                subsystem = entry.get("subsystem")
                value = entry.get("value")
                if name is None or subsystem is None:
                    self._total_validation_failures += 1
                    continue
                param = self._get_parameter_internal(name, subsystem)
                if param is None:
                    self._total_validation_failures += 1
                    continue
                result = self.validate_value(name, subsystem, value)
                if result != ValidationResult.VALID:
                    self._total_validation_failures += 1
                    continue
                coerced = self._coerce_value(param, value)
                change = self._commit_change(
                    param, coerced, ChangeKind.SET, source
                )
                applied.append(change)
            return applied

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------

    def save_profile(
        self,
        name: str,
        description: str = "",
        parameters: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> TuningProfile:
        """Capture current parameter values into a named profile.

        When ``parameters`` is None all registered parameters are captured.
        Otherwise only the listed qualified names are captured; names that
        do not resolve to a registered parameter are silently skipped.
        """
        with self._lock:
            values: Dict[str, Any] = {}
            if parameters is None:
                for param in self._parameters.values():
                    values[param.qualified_name] = param.current_value
            else:
                for qualified_name in parameters:
                    param = self._parameters.get(qualified_name)
                    if param is not None:
                        values[qualified_name] = param.current_value

            profile = TuningProfile(
                id=uuid.uuid4().hex,
                name=name,
                description=description,
                values=values,
                tags=list(tags) if tags is not None else [],
            )
            self._profiles[profile.id] = profile
            self._total_profile_saves += 1
            return profile

    def apply_profile(
        self, profile_id: str, source: str = "api"
    ) -> List[ParameterChange]:
        """Apply a saved profile, returning the changes that were applied.

        Only parameters whose value differs from the profile value produce
        a change entry. Each change is also dispatched to watchers.

        Raises:
            ValueError: If the profile id is unknown.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise ValueError(f"Unknown profile '{profile_id}'")

            changes: List[ParameterChange] = []
            for qualified_name, value in profile.values.items():
                param = self._parameters.get(qualified_name)
                if param is None:
                    continue
                result = self.validate_value(
                    param.name, param.subsystem, value
                )
                if result != ValidationResult.VALID:
                    self._total_validation_failures += 1
                    continue
                coerced = self._coerce_value(param, value)
                if coerced == param.current_value:
                    continue
                change = self._commit_change(
                    param,
                    coerced,
                    ChangeKind.PROFILE_APPLIED,
                    source,
                    profile_id=profile.id,
                )
                changes.append(change)
            profile.updated_at = _datetime.utcnow().isoformat()
            return changes

    def get_profile(self, profile_id: str) -> Optional[TuningProfile]:
        """Return a profile by id, or None if absent."""
        with self._lock:
            return self._profiles.get(profile_id)

    def list_profiles(
        self, tag: Optional[str] = None
    ) -> List[TuningProfile]:
        """List saved profiles, optionally filtered by tag."""
        with self._lock:
            results: List[TuningProfile] = []
            for profile in self._profiles.values():
                if tag is not None and tag not in profile.tags:
                    continue
                results.append(profile)
            return results

    def remove_profile(self, profile_id: str) -> bool:
        """Remove a saved profile. Returns True if removed."""
        with self._lock:
            if profile_id not in self._profiles:
                return False
            del self._profiles[profile_id]
            return True

    def diff_profile(
        self, profile_id: str
    ) -> List[TuningDiff]:
        """Compare current values against a profile, returning differences.

        Only parameters present in the profile whose current value differs
        from the profile value are included. The ``difference`` field holds
        ``profile_value - current_value`` for numeric values and None
        otherwise.

        Raises:
            ValueError: If the profile id is unknown.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise ValueError(f"Unknown profile '{profile_id}'")

            diffs: List[TuningDiff] = []
            for qualified_name, profile_value in profile.values.items():
                param = self._parameters.get(qualified_name)
                if param is None:
                    continue
                current_value = param.current_value
                if current_value == profile_value:
                    continue

                difference: Optional[Union[int, float]] = None
                if isinstance(profile_value, (int, float)) and not isinstance(
                    profile_value, bool
                ) and isinstance(current_value, (int, float)) and not isinstance(
                    current_value, bool
                ):
                    difference = profile_value - current_value

                diffs.append(
                    TuningDiff(
                        parameter_name=param.name,
                        subsystem=param.subsystem,
                        current_value=current_value,
                        profile_value=profile_value,
                        difference=difference,
                    )
                )
            return diffs

    def export_profile(self, profile_id: str) -> Dict[str, Any]:
        """Export a profile as a serializable dictionary.

        Raises:
            ValueError: If the profile id is unknown.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise ValueError(f"Unknown profile '{profile_id}'")
            return profile.to_dict()

    def import_profile(
        self, data: Dict[str, Any], source: str = "api"
    ) -> TuningProfile:
        """Import a profile from a serialized dictionary.

        A fresh identifier is allocated if the supplied identifier is missing
        or already present in the engine, ensuring imports never collide
        with existing profiles.
        """
        with self._lock:
            profile_id = data.get("id") or uuid.uuid4().hex
            if profile_id in self._profiles:
                profile_id = uuid.uuid4().hex

            profile = TuningProfile(
                id=profile_id,
                name=data.get("name", ""),
                description=data.get("description", ""),
                values=dict(data.get("values", {})),
                created_at=data.get("created_at", _datetime.utcnow().isoformat()),
                updated_at=_datetime.utcnow().isoformat(),
                tags=list(data.get("tags", [])),
            )
            self._profiles[profile.id] = profile
            self._total_profile_saves += 1
            return profile

    # ------------------------------------------------------------------
    # Watchers
    # ------------------------------------------------------------------

    def watch(
        self,
        parameter_name: str,
        callback: Callable[[ParameterChange], None],
    ) -> str:
        """Subscribe to changes for a parameter (or ``"*"`` for all).

        Returns the watcher id, which can be passed to :meth:`unwatch`.
        """
        with self._lock:
            watcher = ParameterWatcher(
                id=uuid.uuid4().hex,
                parameter_name=parameter_name,
                callback=callback,
                active=True,
            )
            self._watchers[watcher.id] = watcher
            return watcher.id

    def unwatch(self, watcher_id: str) -> bool:
        """Remove a watcher subscription. Returns True if removed."""
        with self._lock:
            if watcher_id not in self._watchers:
                return False
            del self._watchers[watcher_id]
            return True

    def list_watchers(self) -> List[ParameterWatcher]:
        """Return all registered watchers."""
        with self._lock:
            return list(self._watchers.values())

    # ------------------------------------------------------------------
    # Change log
    # ------------------------------------------------------------------

    def list_changes(
        self,
        parameter_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[ParameterChange]:
        """Return recent change entries, optionally filtered by parameter.

        The most recent ``limit`` entries are returned in chronological
        order (oldest first among the selected window).
        """
        with self._lock:
            if parameter_name is None:
                selected = list(self._changes)
            else:
                selected = [
                    change
                    for change in self._changes
                    if change.parameter_name == parameter_name
                ]
            if limit <= 0:
                return []
            return selected[-limit:]

    # ------------------------------------------------------------------
    # Status and snapshots
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a dictionary of operational statistics."""
        with self._lock:
            return {
                "total_parameters": len(self._parameters),
                "total_profiles": len(self._profiles),
                "total_watchers": len(self._watchers),
                "total_changes": len(self._changes),
                "total_sets": self._total_sets,
                "total_resets": self._total_resets,
                "total_profile_applies": self._total_profile_applies,
                "total_profile_saves": self._total_profile_saves,
                "total_validation_failures": self._total_validation_failures,
                "last_change_at": self._last_change_at,
            }

    def get_snapshot(self) -> TuningSnapshot:
        """Return an aggregate snapshot of the engine state."""
        with self._lock:
            return TuningSnapshot(
                parameter_count=len(self._parameters),
                profile_count=len(self._profiles),
                watcher_count=len(self._watchers),
                change_count=len(self._changes),
                subsystems=self.list_subsystems(),
                stats=self.get_status(),
            )

    # ------------------------------------------------------------------
    # Reset all state
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all state including parameters, profiles, watchers, changes.

        Seed parameters are re-registered after clearing so the engine
        returns to its initial configuration.
        """
        with self._lock:
            self._parameters.clear()
            self._profiles.clear()
            self._watchers.clear()
            self._changes.clear()

            self._total_sets = 0
            self._total_resets = 0
            self._total_profile_applies = 0
            self._total_profile_saves = 0
            self._total_validation_failures = 0
            self._last_change_at = ""

            self._initialize_seed_parameters()


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_live_tuning() -> LiveTuningEngine:
    """Return the shared :class:`LiveTuningEngine` singleton instance."""
    return LiveTuningEngine.get_instance()
