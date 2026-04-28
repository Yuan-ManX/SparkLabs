"""
SparkAI Agent - Debug Skill

Debug Skills maintain a living protocol of verified fixes.
They enable agents to systematically repair integration errors
rather than patching isolated syntax bugs.

The debug protocol records error patterns, verified solutions,
and builds a knowledge base that improves over time.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.agent.skills.base import Skill, SkillRegistry


@dataclass
class DebugEntry:
    """
    A verified debug fix entry.

    Records an error pattern, its root cause, and the
    verified solution that resolved it.
    """

    error_pattern: str = ""
    error_type: str = ""
    root_cause: str = ""
    solution: str = ""
    verification_command: str = ""
    category: str = "general"
    success_count: int = 0
    fail_count: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def reliability(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5
        return self.success_count / total

    def record_success(self) -> None:
        self.success_count += 1

    def record_failure(self) -> None:
        self.fail_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "error_pattern": self.error_pattern,
            "error_type": self.error_type,
            "root_cause": self.root_cause,
            "solution": self.solution,
            "verification_command": self.verification_command,
            "category": self.category,
            "reliability": self.reliability,
        }


class DebugProtocol:
    """
    Living protocol of verified debug fixes.

    Maintains a knowledge base of error patterns and their
    verified solutions. Agents query this protocol when
    encountering errors to find proven fixes.
    """

    def __init__(self):
        self._entries: Dict[str, DebugEntry] = {}
        self._pattern_index: Dict[str, List[str]] = {}
        self._load_builtin_entries()

    def _load_builtin_entries(self) -> None:
        builtin = [
            DebugEntry(
                error_pattern="ImportError",
                error_type="import",
                root_cause="Missing module or incorrect import path",
                solution="Check module installation and import paths",
                verification_command="python -c 'import <module>'",
                category="python",
            ),
            DebugEntry(
                error_pattern="ModuleNotFoundError",
                error_type="import",
                root_cause="Module not installed or not in PYTHONPATH",
                solution="Install the module or add to PYTHONPATH",
                verification_command="pip install <module>",
                category="python",
            ),
            DebugEntry(
                error_pattern="TypeError.*NoneType",
                error_type="null_reference",
                root_cause="Accessing attribute on None object",
                solution="Add null check before accessing attributes",
                verification_command="Run the function with test inputs",
                category="python",
            ),
            DebugEntry(
                error_pattern="KeyError",
                error_type="data_access",
                root_cause="Accessing non-existent dictionary key",
                solution="Use .get() with default or check key existence",
                verification_command="Run the data access code",
                category="python",
            ),
            DebugEntry(
                error_pattern="CORS",
                error_type="network",
                root_cause="Cross-origin request blocked by browser",
                solution="Add CORS middleware to the backend server",
                verification_command="curl -H 'Origin: http://localhost:3000' http://localhost:8091/api/health",
                category="network",
            ),
            DebugEntry(
                error_pattern="WebSocket.*connection.*refused",
                error_type="network",
                root_cause="WebSocket server not running or wrong port",
                solution="Start the WebSocket server and verify the port",
                verification_command="curl http://localhost:8091/api/health",
                category="network",
            ),
            DebugEntry(
                error_pattern="Cannot read properties of undefined",
                error_type="null_reference",
                root_cause="Accessing property on undefined JavaScript object",
                solution="Add null/undefined check before property access",
                verification_command="Run the component in the browser",
                category="typescript",
            ),
            DebugEntry(
                error_pattern="Component.*not found",
                error_type="ecs",
                root_cause="ECS component type not registered",
                solution="Register the component class with ComponentRegistry",
                verification_command="Check ComponentRegistry.list_types()",
                category="engine",
            ),
            DebugEntry(
                error_pattern="System.*not found",
                error_type="ecs",
                root_cause="ECS system type not registered",
                solution="Register the system class with SystemRegistry",
                verification_command="Check SystemRegistry.list_types()",
                category="engine",
            ),
        ]
        for entry in builtin:
            self._entries[entry.id] = entry
            key = entry.error_type
            if key not in self._pattern_index:
                self._pattern_index[key] = []
            self._pattern_index[key].append(entry.id)

    def register(self, entry: DebugEntry) -> None:
        self._entries[entry.id] = entry
        key = entry.error_type
        if key not in self._pattern_index:
            self._pattern_index[key] = []
        self._pattern_index[key].append(entry.id)

    def find_by_pattern(self, error_message: str) -> List[DebugEntry]:
        import re
        matches = []
        for entry in self._entries.values():
            try:
                if re.search(entry.error_pattern, error_message, re.IGNORECASE):
                    matches.append(entry)
            except re.error:
                if entry.error_pattern.lower() in error_message.lower():
                    matches.append(entry)
        matches.sort(key=lambda e: e.reliability, reverse=True)
        return matches

    def find_by_type(self, error_type: str) -> List[DebugEntry]:
        ids = self._pattern_index.get(error_type, [])
        return [self._entries[eid] for eid in ids if eid in self._entries]

    def find_best_fix(self, error_message: str) -> Optional[DebugEntry]:
        matches = self.find_by_pattern(error_message)
        return matches[0] if matches else None

    def list_entries(self) -> List[DebugEntry]:
        return list(self._entries.values())

    def list_error_types(self) -> List[str]:
        return list(self._pattern_index.keys())


class DebugSkill(Skill):
    """
    Skill for systematic debugging with verified fix protocols.

    This skill maintains a living knowledge base of error
    patterns and verified solutions, enabling agents to
    systematically repair errors rather than patching symptoms.
    """

    def __init__(self):
        super().__init__(
            name="debug_skill",
            description="Systematically debug game engine errors using verified fix protocols",
            category="debugging",
            instructions=(
                "Use this skill to systematically debug errors.\n"
                "1. Identify the error pattern from the error message\n"
                "2. Look up verified fixes in the debug protocol\n"
                "3. Apply the fix and verify with the verification command\n"
                "4. Record the outcome to improve the protocol"
            ),
            steps=[
                "Capture the full error message and stack trace",
                "Identify the error type and pattern",
                "Query the debug protocol for matching fixes",
                "Apply the highest-reliability fix",
                "Run the verification command",
                "Record the outcome (success or failure)",
            ],
            verification=[
                "Error is resolved and no longer occurs",
                "Verification command passes",
                "No new errors introduced by the fix",
            ],
        )
        self._protocol = DebugProtocol()

    @property
    def protocol(self) -> DebugProtocol:
        return self._protocol

    def diagnose(self, error_message: str) -> Dict[str, Any]:
        fix = self._protocol.find_best_fix(error_message)
        if fix:
            return {
                "error_message": error_message,
                "matched_pattern": fix.error_pattern,
                "root_cause": fix.root_cause,
                "solution": fix.solution,
                "verification": fix.verification_command,
                "reliability": fix.reliability,
            }
        return {
            "error_message": error_message,
            "matched_pattern": None,
            "root_cause": "Unknown - no matching pattern found",
            "solution": "Investigate the error manually",
            "verification": "Reproduce and analyze the error",
        }


SkillRegistry.register(DebugSkill())
