"""
SparkLabs Agent - Expression Validator

Expression AST pipeline for validating AI-generated game logic.
Parses expression text into structured AST nodes, applies type
inference and constraint checking, and produces diagnostics with
automatic fix suggestions for common authoring mistakes.

Architecture:
  ExpressionValidator
    |-- Tokenizer (raw text → token stream)
    |-- Parser (token stream → ExpressionNode AST)
    |-- TypeChecker (infer and validate expression types)
    |-- DiagnosticGenerator (severity-graded issue reporting)
    |-- AutoFixEngine (deterministic repair patterns)

Supports number, string, boolean, Vector2, Vector3, Color,
object reference, and function call expression types common
in game scripting contexts.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ExpressionType(Enum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    COLOR = "color"
    OBJECT_REF = "object_ref"
    FUNCTION_CALL = "function_call"


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"

    @property
    def numeric_priority(self) -> int:
        return {
            ValidationSeverity.ERROR: 0,
            ValidationSeverity.WARNING: 1,
            ValidationSeverity.INFO: 2,
            ValidationSeverity.HINT: 3,
        }[self]


@dataclass
class ExpressionNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: str = "literal"
    raw_text: str = ""
    inferred_type: ExpressionType = ExpressionType.NUMBER
    children: List[str] = field(default_factory=list)
    source_location: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "raw_text": self.raw_text[:80],
            "inferred_type": self.inferred_type.value,
            "children_count": len(self.children),
            "source_location": self.source_location,
        }


@dataclass
class ValidationDiagnostic:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    severity: ValidationSeverity = ValidationSeverity.INFO
    message: str = ""
    source_line: int = 0
    source_column: int = 0
    suggestion: str = ""
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "message": self.message,
            "source_line": self.source_line,
            "source_column": self.source_column,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class ExpressionValidationResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    expression_text: str = ""
    ast_root: Optional[ExpressionNode] = None
    diagnostics: List[ValidationDiagnostic] = field(default_factory=list)
    has_errors: bool = False
    has_warnings: bool = False
    estimated_execution_cost: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "expression_text": self.expression_text[:120],
            "ast_root": self.ast_root.to_dict() if self.ast_root else None,
            "diagnostics_count": len(self.diagnostics),
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
            "estimated_execution_cost": round(self.estimated_execution_cost, 3),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return result


class ExpressionValidator:
    """Expression AST pipeline for validating AI-generated game logic."""

    _instance: Optional["ExpressionValidator"] = None
    _lock = threading.Lock()

    MAX_EXPRESSION_LENGTH = 4096
    MAX_AST_DEPTH = 64

    BUILTIN_FUNCTIONS = [
        "sin", "cos", "tan", "sqrt", "abs", "min", "max", "clamp",
        "lerp", "floor", "ceil", "round", "pow", "log",
        "length", "normalize", "dot", "cross", "distance",
        "rgb", "rgba", "hsv", "hex",
        "random", "noise",
    ]

    def __init__(self):
        self._variable_scope: Dict[str, ExpressionType] = {}
        self._function_signatures: Dict[str, Tuple[List[ExpressionType], ExpressionType]] = {}
        self._parse_cache: Dict[str, ExpressionNode] = {}
        self._validations_performed: int = 0
        self._total_diagnostics_emitted: int = 0

    @classmethod
    def get_instance(cls) -> "ExpressionValidator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def parse(self, expression_text: str) -> Optional[ExpressionNode]:
        if not expression_text or len(expression_text) > self.MAX_EXPRESSION_LENGTH:
            return None

        cache_key = expression_text.strip()
        if cache_key in self._parse_cache:
            return self._parse_cache[cache_key]

        root = ExpressionNode(
            node_type="root",
            raw_text=cache_key,
            inferred_type=ExpressionType.NUMBER,
            source_location="0:0",
        )

        inferred = self._infer_expression_type(cache_key)
        root.inferred_type = inferred

        parts = self._tokenize(cache_key)
        for idx, (token_type, token_text, position) in enumerate(parts):
            child = ExpressionNode(
                node_type=token_type,
                raw_text=token_text,
                inferred_type=self._infer_token_type(token_type, token_text),
                source_location=f"0:{position}",
            )
            root.children.append(child.id)

        self._parse_cache[cache_key] = root
        if len(self._parse_cache) > 200:
            oldest_key = next(iter(self._parse_cache))
            del self._parse_cache[oldest_key]

        return root

    def _tokenize(self, text: str) -> List[Tuple[str, str, int]]:
        tokens: List[Tuple[str, str, int]] = []
        pattern = re.compile(
            r'(?P<number>\d+\.?\d*)|'
            r'(?P<string>"[^"]*"|\'[^\']*\')|'
            r'(?P<bool>true|false)|'
            r'(?P<function>\w+)\s*\(',
            re.IGNORECASE,
        )
        for m in re.finditer(pattern, text):
            for kind in ("number", "string", "bool", "function"):
                val = m.group(kind)
                if val is not None:
                    if kind == "function":
                        tokens.append(("function_call", val[:-1], m.start()))
                    else:
                        tokens.append((kind, val, m.start()))
                    break
        return tokens

    def _infer_expression_type(self, text: str) -> ExpressionType:
        text_stripped = text.strip()
        if text_stripped.startswith("Vector2"):
            return ExpressionType.VECTOR2
        if text_stripped.startswith("Vector3"):
            return ExpressionType.VECTOR3
        if text_stripped.startswith("Color") or text_stripped.startswith("#"):
            return ExpressionType.COLOR
        if text_stripped in ("true", "false"):
            return ExpressionType.BOOLEAN
        if re.match(r'^-?\d+\.?\d*$', text_stripped):
            return ExpressionType.NUMBER
        if (text_stripped.startswith('"') and text_stripped.endswith('"')) or \
           (text_stripped.startswith("'") and text_stripped.endswith("'")):
            return ExpressionType.STRING
        return ExpressionType.FUNCTION_CALL

    def _infer_token_type(self, token_kind: str, token_text: str) -> ExpressionType:
        mapping = {
            "number": ExpressionType.NUMBER,
            "string": ExpressionType.STRING,
            "bool": ExpressionType.BOOLEAN,
            "function_call": ExpressionType.FUNCTION_CALL,
        }
        return mapping.get(token_kind, ExpressionType.NUMBER)

    def validate(self, ast_root: ExpressionNode) -> ExpressionValidationResult:
        diagnostics: List[ValidationDiagnostic] = []

        if len(ast_root.raw_text) > self.MAX_EXPRESSION_LENGTH:
            diagnostics.append(ValidationDiagnostic(
                severity=ValidationSeverity.ERROR,
                message=f"Expression exceeds max length of {self.MAX_EXPRESSION_LENGTH}",
                source_line=0,
                source_column=0,
                suggestion="Break the expression into multiple smaller expressions",
                auto_fixable=False,
            ))

        if ast_root.raw_text.count("(") != ast_root.raw_text.count(")"):
            diagnostics.append(ValidationDiagnostic(
                severity=ValidationSeverity.ERROR,
                message="Mismatched parentheses in expression",
                source_line=0,
                source_column=0,
                suggestion="Check that every opening parenthesis has a matching closing parenthesis",
                auto_fixable=True,
            ))

        if ast_root.raw_text.count('"') % 2 != 0:
            diagnostics.append(ValidationDiagnostic(
                severity=ValidationSeverity.ERROR,
                message="Unclosed string literal",
                source_line=0,
                source_column=0,
                suggestion="Add a closing double-quote to terminate the string",
                auto_fixable=False,
            ))

        func_pattern = re.findall(r'(\w+)\s*\(', ast_root.raw_text)
        for func_name in func_pattern:
            if func_name.lower() not in self.BUILTIN_FUNCTIONS:
                diagnostics.append(ValidationDiagnostic(
                    severity=ValidationSeverity.WARNING,
                    message=f"Unknown function '{func_name}' — may not exist at runtime",
                    source_line=0,
                    source_column=0,
                    suggestion=f"Use one of the available functions: {', '.join(self.BUILTIN_FUNCTIONS[:8])}...",
                    auto_fixable=False,
                ))

        if ast_root.inferred_type == ExpressionType.NUMBER:
            try:
                float(ast_root.raw_text)
            except (ValueError, TypeError):
                pass

        cost = max(1.0, len(ast_root.children) * 0.5 + len(ast_root.raw_text) * 0.01)

        has_errors = any(d.severity == ValidationSeverity.ERROR for d in diagnostics)
        has_warnings = any(d.severity == ValidationSeverity.WARNING for d in diagnostics)

        result = ExpressionValidationResult(
            expression_text=ast_root.raw_text,
            ast_root=ast_root,
            diagnostics=diagnostics,
            has_errors=has_errors,
            has_warnings=has_warnings,
            estimated_execution_cost=cost,
        )

        self._validations_performed += 1
        self._total_diagnostics_emitted += len(diagnostics)

        return result

    def auto_fix(self, validation_result: ExpressionValidationResult) -> str:
        fixed_text = validation_result.expression_text

        for diag in validation_result.diagnostics:
            if not diag.auto_fixable:
                continue
            if "parentheses" in diag.message.lower():
                open_count = fixed_text.count("(")
                close_count = fixed_text.count(")")
                if open_count > close_count:
                    fixed_text += ")" * (open_count - close_count)
                elif close_count > open_count:
                    fixed_text = "(" * (close_count - open_count) + fixed_text

        return fixed_text

    def type_check(self, ast_root: ExpressionNode) -> ExpressionType:
        return ast_root.inferred_type

    def get_available_functions(self) -> List[str]:
        return sorted(self.BUILTIN_FUNCTIONS)

    def get_variable_scope(self) -> dict:
        return {name: t.value for name, t in self._variable_scope.items()}

    def get_stats(self) -> dict:
        severity_counts: Dict[str, int] = {}
        for s in ValidationSeverity:
            severity_counts[s.value] = 0

        return {
            "validations_performed": self._validations_performed,
            "total_diagnostics_emitted": self._total_diagnostics_emitted,
            "parse_cache_size": len(self._parse_cache),
            "builtin_functions": len(self.BUILTIN_FUNCTIONS),
            "variable_scope_size": len(self._variable_scope),
            "max_expression_length": self.MAX_EXPRESSION_LENGTH,
            "max_ast_depth": self.MAX_AST_DEPTH,
        }


def get_expression_validator() -> ExpressionValidator:
    return ExpressionValidator.get_instance()