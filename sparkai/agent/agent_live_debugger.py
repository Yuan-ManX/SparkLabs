"""
SparkLabs Agent - Live Debugger

A runtime debugging module that provides AI-powered error analysis,
state inspection, breakpoint management, and fix suggestion capabilities
for game development. Tracks debug entries, runtime errors, state
snapshots, and generates fix suggestions through pattern matching.

Core capabilities:
  - Debug session lifecycle management
  - Structured log entry collection with level filtering
  - Breakpoint management (line, condition, data-watch, event, exception)
  - Runtime error tracking with deduplication and occurrence counting
  - State snapshot capture for runtime inspection
  - Pattern-matched fix suggestion generation
  - Debug report generation with session statistics

Architecture:
  AgentLiveDebugger (Singleton)
    |-- DebugEntry (dataclass)
    |-- Breakpoint (dataclass)
    |-- StateSnapshot (dataclass)
    |-- RuntimeError (dataclass)
    |-- FixSuggestion (dataclass)
    |-- DebugSession (dataclass)
    |-- start_session()
    |-- log_entry()
    |-- add_breakpoint()
    |-- report_error()
    |-- suggest_fix()
    |-- generate_debug_report()
"""

from __future__ import annotations

import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DebugLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    TRACE = "trace"


class BreakpointType(Enum):
    LINE = "line"
    CONDITION = "condition"
    DATA_WATCH = "data-watch"
    EVENT = "event"
    EXCEPTION = "exception"


class InspectionScope(Enum):
    SCENE = "scene"
    ENTITY = "entity"
    COMPONENT = "component"
    SYSTEM = "system"
    GLOBAL = "global"


class FixConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class DebugEntry:
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    level: DebugLevel = DebugLevel.INFO
    source: str = ""
    message: str = ""
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "stack_trace": self.stack_trace[:500],
            "context": dict(self.context),
            "timestamp": self.timestamp,
            "resolved": self.resolved,
        }


@dataclass
class Breakpoint:
    breakpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    bp_type: BreakpointType = BreakpointType.LINE
    target: str = ""
    enabled: bool = True
    hit_count: int = 0
    max_hits: int = 0
    created_at: float = field(default_factory=_time_module.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breakpoint_id": self.breakpoint_id,
            "name": self.name,
            "bp_type": self.bp_type.value,
            "target": self.target,
            "enabled": self.enabled,
            "hit_count": self.hit_count,
            "max_hits": self.max_hits,
            "created_at": self.created_at,
            "tags": list(self.tags),
        }


@dataclass
class StateSnapshot:
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    scope: InspectionScope = InspectionScope.GLOBAL
    target_name: str = ""
    state_data: Dict[str, Any] = field(default_factory=dict)
    captured_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "scope": self.scope.value,
            "target_name": self.target_name,
            "state_data": dict(self.state_data),
            "captured_at": self.captured_at,
        }


@dataclass
class RuntimeError:
    error_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    error_type: str = ""
    message: str = ""
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    occurrence_count: int = 1
    first_seen: float = field(default_factory=_time_module.time)
    last_seen: float = field(default_factory=_time_module.time)
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "stack_trace": self.stack_trace[:500],
            "context": dict(self.context),
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "resolved": self.resolved,
        }


@dataclass
class FixSuggestion:
    suggestion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    error_id: str = ""
    description: str = ""
    code_snippet: str = ""
    confidence: FixConfidence = FixConfidence.MEDIUM
    applied: bool = False
    applied_at: Optional[float] = None
    success: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "error_id": self.error_id,
            "description": self.description,
            "code_snippet": self.code_snippet,
            "confidence": self.confidence.value,
            "applied": self.applied,
            "applied_at": self.applied_at,
            "success": self.success,
        }


@dataclass
class DebugSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    started_at: float = field(default_factory=_time_module.time)
    entries_count: int = 0
    errors_found: int = 0
    errors_fixed: int = 0
    active_breakpoints: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "started_at": self.started_at,
            "entries_count": self.entries_count,
            "errors_found": self.errors_found,
            "errors_fixed": self.errors_fixed,
            "active_breakpoints": self.active_breakpoints,
        }


# ---------------------------------------------------------------------------
# Fix Suggestion Templates
# ---------------------------------------------------------------------------

_FIX_PATTERNS: Dict[str, Dict[str, Any]] = {
    "nullreference": {
        "description": "Add null-check guard before accessing the reference",
        "code_snippet": "if target is not None:\n    result = target.method()\nelse:\n    result = default_value",
        "confidence": FixConfidence.HIGH,
    },
    "nonetype": {
        "description": "Add None-check guard before accessing the attribute",
        "code_snippet": "if obj is not None:\n    value = obj.attribute\nelse:\n    value = fallback",
        "confidence": FixConfidence.HIGH,
    },
    "indexerror": {
        "description": "Add bounds checking before accessing collection by index",
        "code_snippet": "if 0 <= index < len(collection):\n    item = collection[index]\nelse:\n    item = default",
        "confidence": FixConfidence.HIGH,
    },
    "out of range": {
        "description": "Validate index against collection length before access",
        "code_snippet": "if index < len(items):\n    selected = items[index]\nelse:\n    selected = None",
        "confidence": FixConfidence.HIGH,
    },
    "keyerror": {
        "description": "Use .get() with a default value instead of direct key access",
        "code_snippet": "value = dictionary.get(key, default_value)",
        "confidence": FixConfidence.HIGH,
    },
    "typeerror": {
        "description": "Add explicit type conversion before the operation",
        "code_snippet": "try:\n    converted = target_type(raw_value)\nexcept (ValueError, TypeError):\n    converted = default_value",
        "confidence": FixConfidence.MEDIUM,
    },
    "attributeerror": {
        "description": "Use hasattr() to check attribute existence before access",
        "code_snippet": "if hasattr(obj, 'attribute_name'):\n    value = obj.attribute_name\nelse:\n    value = default",
        "confidence": FixConfidence.HIGH,
    },
    "recursionerror": {
        "description": "Replace unbounded recursion with an iterative approach and depth limit",
        "code_snippet": "max_depth = 1000\nstack = [initial_value]\nwhile stack and len(stack) < max_depth:\n    current = stack.pop()\n    # process current\n    stack.extend(next_items)",
        "confidence": FixConfidence.MEDIUM,
    },
    "timeouterror": {
        "description": "Wrap the operation with a timeout pattern using threading or asyncio",
        "code_snippet": "import threading\n\ndef run_with_timeout(func, args=(), timeout=5.0):\n    result = [None]\n    def target():\n        result[0] = func(*args)\n    t = threading.Thread(target=target)\n    t.start()\n    t.join(timeout)\n    if t.is_alive():\n        raise TimeoutError('Operation timed out')\n    return result[0]",
        "confidence": FixConfidence.MEDIUM,
    },
}

_DEFAULT_FIX: Dict[str, Any] = {
    "description": "Add logging and defensive programming guards around the failing code path",
    "code_snippet": "try:\n    # original operation\n    result = perform_operation()\nexcept Exception as e:\n    log_error(f'Operation failed: {e}')\n    result = fallback_value",
    "confidence": FixConfidence.LOW,
}


# ---------------------------------------------------------------------------
# Singleton Agent
# ---------------------------------------------------------------------------

class AgentLiveDebugger:
    """
    Runtime debugging module that provides AI-powered error analysis,
    state inspection, breakpoint management, and fix suggestion
    capabilities for game development.

    Tracks debug entries across sessions, manages breakpoints with hit
    counting and max-hit limits, captures state snapshots for runtime
    inspection, deduplicates runtime errors by type and message, and
    generates fix suggestions through error-type pattern matching.

    Usage:
        debugger = get_live_debugger()
        session = debugger.start_session("Level 3 Debug")
        debugger.log_entry(DebugLevel.WARNING, "physics", "Collision jitter detected")
        bp = debugger.add_breakpoint("Player Pos", BreakpointType.DATA_WATCH,
            "entity:player:position")
        err = debugger.report_error("KeyError", "Missing spawn_point key",
            "Traceback...")
        fix = debugger.suggest_fix(err.error_id)
    """

    _instance: Optional["AgentLiveDebugger"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentLiveDebugger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentLiveDebugger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._sessions: Dict[str, DebugSession] = {}
        self._entries: List[DebugEntry] = []
        self._breakpoints: Dict[str, Breakpoint] = {}
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._errors: Dict[str, RuntimeError] = {}
        self._suggestions: Dict[str, FixSuggestion] = {}
        self._active_session_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(self, name: str) -> DebugSession:
        session = DebugSession(name=name)
        self._sessions[session.session_id] = session
        self._active_session_id = session.session_id
        return session

    def end_session(self, session_id: str) -> Optional[DebugSession]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        unresolved_entries = sum(
            1 for e in self._entries if not e.resolved
        )
        unresolved_errors = sum(
            1 for err in self._errors.values() if not err.resolved
        )
        active_bps = sum(
            1 for bp in self._breakpoints.values() if bp.enabled
        )

        session.entries_count = len(self._entries)
        session.errors_found = len(self._errors)
        session.errors_fixed = len(self._errors) - unresolved_errors
        session.active_breakpoints = active_bps

        if self._active_session_id == session_id:
            self._active_session_id = None

        return session

    def get_active_session(self) -> Optional[DebugSession]:
        if self._active_session_id is None:
            return None
        return self._sessions.get(self._active_session_id)

    # ------------------------------------------------------------------
    # Log Entries
    # ------------------------------------------------------------------

    def log_entry(
        self,
        level: DebugLevel,
        source: str,
        message: str,
        stack_trace: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> DebugEntry:
        entry = DebugEntry(
            level=level,
            source=source,
            message=message,
            stack_trace=stack_trace,
            context=context if context is not None else {},
        )
        self._entries.append(entry)

        session = self.get_active_session()
        if session:
            session.entries_count += 1

        return entry

    def get_entries(
        self,
        level: Optional[DebugLevel] = None,
        source: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 50,
    ) -> List[DebugEntry]:
        results = list(self._entries)
        if level is not None:
            results = [e for e in results if e.level == level]
        if source is not None:
            results = [e for e in results if e.source == source]
        if resolved is not None:
            results = [e for e in results if e.resolved == resolved]
        return results[-limit:]

    def resolve_entry(self, entry_id: str) -> bool:
        for entry in self._entries:
            if entry.entry_id == entry_id:
                entry.resolved = True
                return True
        return False

    def mark_entries_resolved(self, source: str) -> int:
        count = 0
        for entry in self._entries:
            if entry.source == source and not entry.resolved:
                entry.resolved = True
                count += 1
        return count

    # ------------------------------------------------------------------
    # Breakpoint Management
    # ------------------------------------------------------------------

    def add_breakpoint(
        self,
        name: str,
        bp_type: BreakpointType,
        target: str,
        max_hits: int = 0,
        tags: Optional[List[str]] = None,
    ) -> Breakpoint:
        bp = Breakpoint(
            name=name,
            bp_type=bp_type,
            target=target,
            max_hits=max_hits,
            tags=tags if tags is not None else [],
        )
        self._breakpoints[bp.breakpoint_id] = bp

        session = self.get_active_session()
        if session:
            session.active_breakpoints += 1

        return bp

    def enable_breakpoint(self, breakpoint_id: str) -> bool:
        bp = self._breakpoints.get(breakpoint_id)
        if bp is None:
            return False
        bp.enabled = True
        return True

    def disable_breakpoint(self, breakpoint_id: str) -> bool:
        bp = self._breakpoints.get(breakpoint_id)
        if bp is None:
            return False
        bp.enabled = False

        session = self.get_active_session()
        if session:
            session.active_breakpoints = sum(
                1 for b in self._breakpoints.values() if b.enabled
            )
        return True

    def hit_breakpoint(self, breakpoint_id: str) -> bool:
        bp = self._breakpoints.get(breakpoint_id)
        if bp is None:
            return False
        if not bp.enabled:
            return False
        bp.hit_count += 1
        if bp.max_hits == 0:
            return True
        return bp.hit_count <= bp.max_hits

    def get_active_breakpoints(self) -> List[Breakpoint]:
        return [bp for bp in self._breakpoints.values() if bp.enabled]

    def get_breakpoints_by_tag(self, tag: str) -> List[Breakpoint]:
        return [bp for bp in self._breakpoints.values() if tag in bp.tags]

    # ------------------------------------------------------------------
    # State Snapshots
    # ------------------------------------------------------------------

    def take_snapshot(
        self,
        scope: InspectionScope,
        target_name: str,
        state_data: Dict[str, Any],
    ) -> StateSnapshot:
        snapshot = StateSnapshot(
            scope=scope,
            target_name=target_name,
            state_data=state_data,
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def get_snapshots(
        self,
        scope: Optional[InspectionScope] = None,
        limit: int = 20,
    ) -> List[StateSnapshot]:
        results = list(self._snapshots.values())
        if scope is not None:
            results = [s for s in results if s.scope == scope]
        results.sort(key=lambda s: s.captured_at, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Runtime Error Tracking
    # ------------------------------------------------------------------

    def report_error(
        self,
        error_type: str,
        message: str,
        stack_trace: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RuntimeError:
        existing = self._find_similar_error(error_type, message)
        if existing is not None:
            existing.occurrence_count += 1
            existing.last_seen = _time_module.time()
            if context is not None:
                existing.context.update(context)
            return existing

        error = RuntimeError(
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            context=context if context is not None else {},
        )
        self._errors[error.error_id] = error

        session = self.get_active_session()
        if session:
            session.errors_found += 1

        return error

    def get_unresolved_errors(self) -> List[RuntimeError]:
        return [err for err in self._errors.values() if not err.resolved]

    def resolve_error(self, error_id: str) -> bool:
        error = self._errors.get(error_id)
        if error is None:
            return False
        error.resolved = True

        session = self.get_active_session()
        if session:
            session.errors_fixed += 1

        return True

    def _find_similar_error(
        self, error_type: str, message: str
    ) -> Optional[RuntimeError]:
        error_type_lower = error_type.lower()
        message_lower = message.lower()
        for error in self._errors.values():
            if error.error_type.lower() == error_type_lower:
                if error.message.lower() == message_lower:
                    return error
        return None

    # ------------------------------------------------------------------
    # Fix Suggestions
    # ------------------------------------------------------------------

    def suggest_fix(self, error_id: str) -> Optional[FixSuggestion]:
        error = self._errors.get(error_id)
        if error is None:
            return None

        error_type_lower = error.error_type.lower()
        message_lower = error.message.lower()

        pattern = None
        for key, fix_data in _FIX_PATTERNS.items():
            if key in error_type_lower or key in message_lower:
                pattern = fix_data
                break

        if pattern is None:
            pattern = _DEFAULT_FIX

        suggestion = FixSuggestion(
            error_id=error_id,
            description=pattern["description"],
            code_snippet=pattern["code_snippet"],
            confidence=pattern["confidence"],
        )
        self._suggestions[suggestion.suggestion_id] = suggestion
        return suggestion

    def apply_fix(self, suggestion_id: str) -> bool:
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is None:
            return False
        suggestion.applied = True
        suggestion.applied_at = _time_module.time()

        error = self._errors.get(suggestion.error_id)
        if error:
            error.resolved = True

            session = self.get_active_session()
            if session:
                session.errors_fixed += 1

        return True

    # ------------------------------------------------------------------
    # Statistics and Reports
    # ------------------------------------------------------------------

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {
                "session_entries": 0,
                "error_rate": 0.0,
                "avg_fix_confidence": 0.0,
                "breakpoints_hit": 0,
            }

        total_entries = len(self._entries)
        total_errors = len(self._errors)
        error_rate = round(total_errors / max(total_entries, 1), 4)

        total_bp_hits = sum(bp.hit_count for bp in self._breakpoints.values())

        confidences = [s.confidence for s in self._suggestions.values()]
        if confidences:
            confidence_map = {
                FixConfidence.HIGH: 1.0,
                FixConfidence.MEDIUM: 0.66,
                FixConfidence.LOW: 0.33,
                FixConfidence.SPECULATIVE: 0.1,
            }
            avg_conf = sum(confidence_map.get(c, 0.33) for c in confidences) / len(confidences)
        else:
            avg_conf = 0.0

        return {
            "session_entries": total_entries,
            "error_rate": error_rate,
            "avg_fix_confidence": round(avg_conf, 2),
            "breakpoints_hit": total_bp_hits,
        }

    def generate_debug_report(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)

        unresolved_errors = self.get_unresolved_errors()
        errors_list = [err.to_dict() for err in unresolved_errors]

        enabled_bps = self.get_active_breakpoints()
        breakpoints_summary = {
            "total": len(self._breakpoints),
            "active": len(enabled_bps),
            "total_hits": sum(bp.hit_count for bp in self._breakpoints.values()),
            "breakpoints": [bp.to_dict() for bp in enabled_bps],
        }

        fix_suggestions = [s.to_dict() for s in self._suggestions.values()]

        summary = {
            "session_name": session.name if session else "unknown",
            "session_id": session_id,
            "total_entries": len(self._entries),
            "total_errors": len(self._errors),
            "unresolved_errors": len(unresolved_errors),
            "total_suggestions": len(self._suggestions),
            "generated_at": _time_module.time(),
        }

        return {
            "summary": summary,
            "errors_list": errors_list,
            "breakpoints_summary": breakpoints_summary,
            "fix_suggestions": fix_suggestions,
        }

    def clear_old_entries(self, older_than_seconds: int = 3600) -> int:
        now = _time_module.time()
        threshold = now - older_than_seconds
        original_count = len(self._entries)
        self._entries = [e for e in self._entries if e.timestamp >= threshold]
        return original_count - len(self._entries)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[DebugSession]:
        return self._sessions.get(session_id)

    def get_error(self, error_id: str) -> Optional[RuntimeError]:
        return self._errors.get(error_id)

    def get_suggestion(self, suggestion_id: str) -> Optional[FixSuggestion]:
        return self._suggestions.get(suggestion_id)

    def get_stats(self) -> Dict[str, Any]:
        total_entries = len(self._entries)
        resolved_entries = sum(1 for e in self._entries if e.resolved)
        total_errors = len(self._errors)
        unresolved_errors = sum(1 for e in self._errors.values() if not e.resolved)
        total_breakpoints = len(self._breakpoints)
        active_breakpoints = sum(1 for b in self._breakpoints.values() if b.enabled)
        total_suggestions = len(self._suggestions)
        applied_suggestions = sum(1 for s in self._suggestions.values() if s.applied)

        level_breakdown: Dict[str, int] = {}
        for entry in self._entries:
            key = entry.level.value
            level_breakdown[key] = level_breakdown.get(key, 0) + 1

        return {
            "total_sessions": len(self._sessions),
            "total_entries": total_entries,
            "resolved_entries": resolved_entries,
            "total_errors": total_errors,
            "unresolved_errors": unresolved_errors,
            "total_breakpoints": total_breakpoints,
            "active_breakpoints": active_breakpoints,
            "total_snapshots": len(self._snapshots),
            "total_suggestions": total_suggestions,
            "applied_suggestions": applied_suggestions,
            "level_breakdown": level_breakdown,
        }


def get_live_debugger() -> AgentLiveDebugger:
    return AgentLiveDebugger.get_instance()