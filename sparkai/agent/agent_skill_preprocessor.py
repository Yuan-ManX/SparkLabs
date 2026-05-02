"""
Skill Preprocessor - Pre-execution validation and parameter normalization.

Architecture:
    SkillPreprocessor/
    |-- ValidationResult (validation outcome classification)
    |-- ParamConstraint (parameter validation rules)
    |-- SkillSpec (complete skill specification)
    |-- ValidationReport (detailed validation output)
    |-- SkillPreprocessor (unified preprocessing engine)

Validates skill invocation parameters before execution, applies type coercion,
checks preconditions, and normalizes inputs for consistent agent behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union


class ValidationResult(Enum):
    PASS = auto()
    WARN = auto()
    FAIL = auto()


@dataclass
class ParamConstraint:
    name: str
    param_type: type = str
    required: bool = False
    default: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    description: str = ""
    coerce: bool = True
    _compiled_pattern: Optional[re.Pattern] = None

    def validate(self, value: Any) -> Tuple[ValidationResult, str]:
        if value is None:
            if self.required:
                return ValidationResult.FAIL, f"Required parameter '{self.name}' is missing"
            return ValidationResult.PASS, ""

        if self.allowed_values and value not in self.allowed_values:
            return ValidationResult.FAIL, (
                f"Value '{value}' not in allowed values: {self.allowed_values}"
            )

        if isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                return ValidationResult.FAIL, (
                    f"Value {value} below minimum {self.min_value}"
                )
            if self.max_value is not None and value > self.max_value:
                return ValidationResult.FAIL, (
                    f"Value {value} above maximum {self.max_value}"
                )

        if isinstance(value, (str, list, tuple, dict)):
            actual_len = len(value)
            if self.min_length is not None and actual_len < self.min_length:
                return ValidationResult.FAIL, (
                    f"Length {actual_len} below minimum {self.min_length}"
                )
            if self.max_length is not None and actual_len > self.max_length:
                return ValidationResult.WARN, (
                    f"Length {actual_len} exceeds maximum {self.max_length}"
                )

        if self.pattern and isinstance(value, str):
            if self._compiled_pattern is None:
                self._compiled_pattern = re.compile(self.pattern)
            if not self._compiled_pattern.match(value):
                return ValidationResult.FAIL, (
                    f"Value '{value}' does not match pattern '{self.pattern}'"
                )

        if self.param_type and not isinstance(value, self.param_type):
            if self.coerce:
                try:
                    coerced = self.param_type(value)
                    return ValidationResult.PASS, ""
                except (ValueError, TypeError):
                    return ValidationResult.FAIL, (
                        f"Cannot coerce '{value}' to {self.param_type.__name__}"
                    )
            return ValidationResult.WARN, (
                f"Type mismatch: expected {self.param_type.__name__}, got {type(value).__name__}"
            )

        return ValidationResult.PASS, ""

    def normalize(self, value: Any) -> Any:
        if value is None:
            return self.default
        if self.param_type and not isinstance(value, self.param_type) and self.coerce:
            try:
                return self.param_type(value)
            except (ValueError, TypeError):
                return value
        if isinstance(value, str) and self.max_length and len(value) > self.max_length:
            return value[:self.max_length]
        return value


@dataclass
class SkillSpec:
    skill_id: str
    name: str
    description: str = ""
    constraints: List[ParamConstraint] = field(default_factory=list)
    preconditions: List[Callable[[Dict[str, Any]], bool]] = field(default_factory=list)
    required_roles: List[str] = field(default_factory=list)
    min_confidence: float = 0.0
    max_retries: int = 1
    category: str = "general"

    def get_required_params(self) -> List[str]:
        return [c.name for c in self.constraints if c.required]

    def get_all_params(self) -> List[str]:
        return [c.name for c in self.constraints]


@dataclass
class ValidationReport:
    skill_id: str
    skill_name: str
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_params: Dict[str, Any] = field(default_factory=dict)
    missing_params: List[str] = field(default_factory=list)
    extra_params: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "passed": self.passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "missing_params": self.missing_params,
            "extra_params": self.extra_params,
        }


class SkillPreprocessor:
    """Pre-execution skill validation and parameter normalization engine."""

    _instance: Optional["SkillPreprocessor"] = None

    def __init__(self):
        self._specs: Dict[str, SkillSpec] = {}
        self._total_validated = 0
        self._total_passed = 0
        self._total_failed = 0
        self._coercion_log: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "SkillPreprocessor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_skill(self, spec: SkillSpec) -> None:
        self._specs[spec.skill_id] = spec

    def unregister_skill(self, skill_id: str) -> bool:
        if skill_id in self._specs:
            del self._specs[skill_id]
            return True
        return False

    def get_spec(self, skill_id: str) -> Optional[SkillSpec]:
        return self._specs.get(skill_id)

    def validate(self, skill_id: str, params: Dict[str, Any]) -> ValidationReport:
        """Validate and normalize skill parameters before execution."""
        self._total_validated += 1

        spec = self._specs.get(skill_id)
        if not spec:
            self._total_failed += 1
            return ValidationReport(
                skill_id=skill_id, skill_name="unknown",
                passed=False, errors=[f"Unknown skill: {skill_id}"],
            )

        report = ValidationReport(skill_id=skill_id, skill_name=spec.name, passed=True)
        known_params = set(spec.get_all_params())
        required_params = set(spec.get_required_params())
        provided_params = set(params.keys())

        report.missing_params = list(required_params - provided_params)
        report.extra_params = list(provided_params - known_params)

        normalized: Dict[str, Any] = {}

        for constraint in spec.constraints:
            value = params.get(constraint.name)
            result, message = constraint.validate(value)

            if result == ValidationResult.FAIL:
                report.errors.append(message)
                report.passed = False
            elif result == ValidationResult.WARN:
                report.warnings.append(message)

            normalized_value = constraint.normalize(value)
            if normalized_value is not None or constraint.required:
                normalized[constraint.name] = normalized_value

        for key, value in params.items():
            if key not in normalized and key in known_params:
                normalized[key] = value

        if report.missing_params:
            for mp in report.missing_params:
                report.errors.append(f"Missing required parameter: '{mp}'")
            report.passed = False

        if spec.preconditions:
            for precondition in spec.preconditions:
                try:
                    if not precondition(normalized):
                        report.errors.append("Precondition check failed")
                        report.passed = False
                        break
                except Exception as e:
                    report.errors.append(f"Precondition error: {e}")
                    report.passed = False
                    break

        if report.extra_params:
            for ep in report.extra_params:
                report.warnings.append(f"Unexpected parameter: '{ep}'")

        report.normalized_params = normalized

        if report.passed:
            self._total_passed += 1
        else:
            self._total_failed += 1

        return report

    def prepare_context(self, skill_id: str, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Quick validate and prepare execution context."""
        report = self.validate(skill_id, params)
        return report.passed, report.normalized_params, report.errors

    def validate_batch(self, invocations: List[Tuple[str, Dict[str, Any]]]) -> List[ValidationReport]:
        """Validate multiple skill invocations in batch."""
        reports = []
        for skill_id, params in invocations:
            report = self.validate(skill_id, params)
            reports.append(report)
        return reports

    def list_skills(self) -> List[Dict[str, Any]]:
        return [{
            "skill_id": s.skill_id,
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "required_params": s.get_required_params(),
        } for s in self._specs.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_validated": self._total_validated,
            "total_passed": self._total_passed,
            "total_failed": self._total_failed,
            "registered_skills": len(self._specs),
            "pass_rate": (self._total_passed / self._total_validated * 100)
            if self._total_validated > 0 else 100.0,
        }

    def reset(self) -> None:
        self._total_validated = 0
        self._total_passed = 0
        self._total_failed = 0


def get_skill_preprocessor() -> SkillPreprocessor:
    return SkillPreprocessor.get_instance()
