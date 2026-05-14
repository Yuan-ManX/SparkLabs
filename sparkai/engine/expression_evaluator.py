"""
SparkLabs Engine - Expression Evaluator

Expression and formula evaluation system for game logic.
Compiles and evaluates arithmetic, boolean, string, and
conditional expressions with variable substitution, type
checking, and result caching.

Architecture:
  ExpressionEvaluator
    |-- Expression Registry (register, compile, cache expressions)
    |-- Variable Store (typed variable definitions with scoping)
    |-- Evaluator Core (AST-free recursive descent evaluation)
    |-- Validator (expression syntax and type validation)
    |-- Caching Layer (TTL-based result memoization)

Expression Types:
  - ARITHMETIC: a + b * c, (x - y) / 2
  - BOOLEAN: a > 0 and b == true
  - STRING: "Hello " + name
  - COMPARISON: score >= threshold
  - CONDITIONAL: if hp > 0 then "alive" else "dead"
  - FUNCTION_CALL: clamp(value, 0, 100)
  - VARIABLE_REF: direct variable lookup
"""

from __future__ import annotations

import math
import operator
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class ExpressionType(Enum):
    ARITHMETIC = auto()
    BOOLEAN = auto()
    STRING = auto()
    COMPARISON = auto()
    CONDITIONAL = auto()
    FUNCTION_CALL = auto()
    VARIABLE_REF = auto()


class ValueType(Enum):
    INTEGER = auto()
    FLOAT = auto()
    BOOLEAN = auto()
    STRING = auto()
    VECTOR2 = auto()
    VECTOR3 = auto()
    COLOR = auto()
    OBJECT_REF = auto()


# Built-in functions available to expressions
_BUILTIN_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "sqrt": math.sqrt,
    "pow": pow,
    "clamp": lambda v, lo, hi: max(lo, min(v, hi)),
    "lerp": lambda a, b, t: a + (b - a) * t,
    "length": lambda x, y: math.sqrt(x * x + y * y),
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}

_ARITHMETIC_OPS: Dict[str, Callable[[Any, Any], Any]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    "//": operator.floordiv,
    "**": pow,
}

_COMPARISON_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

_LOGICAL_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    "and": lambda a, b: bool(a) and bool(b),
    "or": lambda a, b: bool(a) or bool(b),
}

_TOKEN_PATTERN = re.compile(
    r"""
    \d+\.\d+|\d+                     # numbers
    |"[^"]*"|'[^']*'                 # string literals
    |==|!=|>=|<=|>|<                 # comparison operators
    |\*\*|//|[+\-*/%]               # arithmetic operators
    |\(|\)                           # parentheses
    |,                               # comma
    |and|or|not|if|else|then        # keywords
    |[a-zA-Z_][a-zA-Z0-9_.]*        # identifiers
    """,
    re.VERBOSE,
)


@dataclass
class ExpressionNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    expression_str: str = ""
    expression_type: ExpressionType = ExpressionType.ARITHMETIC
    return_type: ValueType = ValueType.FLOAT
    compiled_ops: List[Any] = field(default_factory=list)
    parameter_names: List[str] = field(default_factory=list)
    context_variables: Dict[str, Any] = field(default_factory=dict)
    cached_result: Any = None
    cache_ttl_seconds: float = 0.0
    last_evaluated_at: float = 0.0
    evaluation_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "expression": self.expression_str,
            "type": self.expression_type.name,
            "return_type": self.return_type.name,
            "parameters": self.parameter_names,
            "evaluation_count": self.evaluation_count,
            "error_count": self.error_count,
        }


@dataclass
class VariableDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    var_type: ValueType = ValueType.INTEGER
    scope: str = "global"
    default_value: Any = 0
    min_value: Any = None
    max_value: Any = None
    is_readonly: bool = False
    is_persistent: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.var_type.name,
            "scope": self.scope,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "is_readonly": self.is_readonly,
            "is_persistent": self.is_persistent,
            "description": self.description,
        }


class ExpressionEvaluator:
    _instance: Optional["ExpressionEvaluator"] = None

    def __init__(self):
        self._expressions: Dict[str, ExpressionNode] = {}
        self._variables: Dict[str, VariableDefinition] = {}
        self._variable_values: Dict[str, Any] = {}
        self._expr_count: int = 0
        self._eval_count: int = 0
        self._error_count: int = 0

    @classmethod
    def get_instance(cls) -> "ExpressionEvaluator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_expression(
        self,
        name: str,
        expression_str: str,
        return_type: ValueType = ValueType.FLOAT,
    ) -> Optional[ExpressionNode]:
        if name in self._expressions:
            return self._expressions[name]

        expr_type = self._classify_expression(expression_str)
        node = ExpressionNode(
            name=name,
            expression_str=expression_str,
            expression_type=expr_type,
            return_type=return_type,
        )
        self._expressions[name] = node
        self._expr_count += 1
        return node

    def evaluate(self, expr_id: str, variables: Optional[Dict[str, Any]] = None) -> Any:
        node = self._expressions.get(expr_id)
        if node is None:
            self._error_count += 1
            return None

        variables = variables or {}

        now = time.time()
        if (
            node.cached_result is not None
            and node.cache_ttl_seconds > 0
            and (now - node.last_evaluated_at) < node.cache_ttl_seconds
        ):
            node.evaluation_count += 1
            self._eval_count += 1
            return node.cached_result

        merged_vars = {**self._variable_values, **variables}
        try:
            result = self._evaluate_internal(node.expression_str, merged_vars)
            node.evaluation_count += 1
            node.last_evaluated_at = now
            if node.cache_ttl_seconds > 0:
                node.cached_result = result
            self._eval_count += 1
            return result
        except Exception:
            node.error_count += 1
            node.last_evaluated_at = now
            self._error_count += 1
            return None

    def define_variable(
        self,
        name: str,
        var_type: ValueType,
        scope: str = "global",
        default_value: Any = None,
    ) -> VariableDefinition:
        if name in self._variables:
            return self._variables[name]

        var_def = VariableDefinition(
            name=name,
            var_type=var_type,
            scope=scope,
            default_value=default_value,
        )
        self._variables[name] = var_def

        if var_def.default_value is not None:
            self._variable_values[name] = var_def.default_value

        return var_def

    def set_variable(self, var_id_or_name: str, value: Any) -> bool:
        var_def = self._variables.get(var_id_or_name)
        if var_def is None:
            var_def = next(
                (v for v in self._variables.values() if v.id == var_id_or_name),
                None,
            )
        if var_def is None:
            return False
        if var_def.is_readonly:
            return False

        if var_def.min_value is not None and isinstance(value, (int, float)):
            if value < var_def.min_value:
                value = var_def.min_value
        if var_def.max_value is not None and isinstance(value, (int, float)):
            if value > var_def.max_value:
                value = var_def.max_value

        self._variable_values[var_def.name] = value
        return True

    def get_variable(self, name_or_id: str) -> Any:
        direct = self._variable_values.get(name_or_id)
        if direct is not None:
            return direct

        var_def = self._variables.get(name_or_id)
        if var_def is not None:
            return self._variable_values.get(var_def.name)

        var_def = next(
            (v for v in self._variables.values() if v.id == name_or_id),
            None,
        )
        if var_def is not None:
            return self._variable_values.get(var_def.name)

        return None

    def compile_expression(self, expr_id: str) -> bool:
        node = self._expressions.get(expr_id)
        if node is None:
            return False

        try:
            tokens = self._tokenize(node.expression_str)
            if not tokens:
                node.error_count += 1
                return False

            node.compiled_ops = tokens
            node.parameter_names = self._extract_parameters(tokens)
            return True
        except Exception:
            node.error_count += 1
            return False

    def validate_expression(self, expression_str: str) -> Dict[str, Any]:
        try:
            tokens = self._tokenize(expression_str)
            if not tokens:
                return {"valid": False, "error": "empty expression"}

            test_vars: Dict[str, Any] = {
                name: 0 for name in self._extract_parameters(tokens)
                if name not in _BUILTIN_FUNCTIONS
            }
            self._evaluate_internal(expression_str, test_vars)

            expr_type = self._classify_expression(expression_str)
            return {
                "valid": True,
                "expression_type": expr_type.name,
                "tokens": tokens,
                "parameters": self._extract_parameters(tokens),
                "error": None,
            }
        except Exception as e:
            return {
                "valid": False,
                "expression_type": None,
                "tokens": [],
                "parameters": [],
                "error": str(e),
            }

    def get_variables_by_scope(self, scope: str) -> List[VariableDefinition]:
        return [
            v for v in self._variables.values()
            if v.scope == scope
        ]

    def get_stats(self) -> Dict[str, Any]:
        scope_counts: Dict[str, int] = {}
        for v in self._variables.values():
            scope_counts[v.scope] = scope_counts.get(v.scope, 0) + 1

        type_counts: Dict[str, int] = {}
        for e in self._expressions.values():
            key = e.expression_type.name
            type_counts[key] = type_counts.get(key, 0) + 1

        return {
            "total_expressions": len(self._expressions),
            "expressions_created": self._expr_count,
            "total_variables": len(self._variables),
            "total_evaluations": self._eval_count,
            "total_errors": self._error_count,
            "expressions_by_type": type_counts,
            "variables_by_scope": scope_counts,
            "error_rate_pct": round(
                (self._error_count / max(self._eval_count, 1)) * 100, 2
            ),
        }

    # --- Internal evaluation ---

    def _evaluate_internal(
        self, expression: str, variables: Dict[str, Any]
    ) -> Any:
        expression = expression.strip()
        tokens = self._tokenize(expression)
        result, _ = self._parse_expr(tokens, 0, variables)
        return result

    @staticmethod
    def _tokenize(expression: str) -> List[str]:
        return [m.group(0) for m in _TOKEN_PATTERN.finditer(expression)]

    def _parse_expr(
        self, tokens: List[str], pos: int, variables: Dict[str, Any]
    ) -> Tuple[Any, int]:
        """Top-level: handles logical ops (and, or) and comparisons (==, !=, >, <, >=, <=)."""
        if pos >= len(tokens):
            return 0, pos

        value, pos = self._parse_term(tokens, pos, variables)

        while pos < len(tokens):
            op_token = tokens[pos]
            if op_token in _COMPARISON_OPS:
                pos += 1
                right_val, pos = self._parse_term(tokens, pos, variables)
                value = _COMPARISON_OPS[op_token](value, right_val)
            elif op_token in ("and", "or"):
                pos += 1
                right_val, pos = self._parse_term(tokens, pos, variables)
                value = _LOGICAL_OPS[op_token](value, right_val)
            else:
                break

        return value, pos

    def _parse_term(
        self, tokens: List[str], pos: int, variables: Dict[str, Any]
    ) -> Tuple[Any, int]:
        """Handles addition and subtraction (+, -)."""
        value, pos = self._parse_factor(tokens, pos, variables)

        while pos < len(tokens) and tokens[pos] in ("+", "-"):
            op_token = tokens[pos]
            pos += 1
            right_val, pos = self._parse_factor(tokens, pos, variables)
            if op_token == "+":
                value = value + right_val
            else:
                value = value - right_val

        return value, pos

    def _parse_factor(
        self, tokens: List[str], pos: int, variables: Dict[str, Any]
    ) -> Tuple[Any, int]:
        """Handles multiplication, division, modulo (*, /, %, //, **)."""
        value, pos = self._parse_primary(tokens, pos, variables)

        while pos < len(tokens) and tokens[pos] in ("*", "/", "%", "//", "**"):
            op_token = tokens[pos]
            pos += 1
            right_val, pos = self._parse_primary(tokens, pos, variables)
            value = _ARITHMETIC_OPS.get(op_token, operator.mul)(value, right_val)

        return value, pos

    def _parse_primary(
        self, tokens: List[str], pos: int, variables: Dict[str, Any]
    ) -> Tuple[Any, int]:
        """Handles atoms: numbers, strings, variables, negation, parens, functions, conditionals."""
        if pos >= len(tokens):
            return 0, pos

        token = tokens[pos]

        # Ternary conditional: if condition then true_val else false_val
        if token in ("if",):
            cond_pos = pos + 1
            cond_val, cond_end = self._parse_expr(tokens, cond_pos, variables)
            if cond_end < len(tokens) and tokens[cond_end] in ("then",):
                then_pos = cond_end + 1
                then_val, then_end = self._parse_expr(tokens, then_pos, variables)
                if then_end < len(tokens) and tokens[then_end] == "else":
                    else_pos = then_end + 1
                    else_val, else_end = self._parse_expr(tokens, else_pos, variables)
                    return (then_val if cond_val else else_val), else_end
            return 0, cond_end

        # Handle negation
        if token == "not":
            next_val, next_pos = self._parse_expr(tokens, pos + 1, variables)
            return not bool(next_val), next_pos

        # Handle parenthesized expressions
        if token == "(":
            inner_val, inner_end = self._parse_expr(tokens, pos + 1, variables)
            if inner_end < len(tokens) and tokens[inner_end] == ")":
                inner_end += 1
            return inner_val, inner_end

        # Handle function calls: func_name(args...)
        if pos + 1 < len(tokens) and tokens[pos + 1] == "(":
            func_name = token
            argc_pos = pos + 2
            args: List[Any] = []
            while argc_pos < len(tokens) and tokens[argc_pos] != ")":
                if tokens[argc_pos] == ",":
                    argc_pos += 1
                    continue
                arg_val, argc_pos = self._parse_expr(tokens, argc_pos, variables)
                args.append(arg_val)
            if argc_pos < len(tokens):
                argc_pos += 1

            func = _BUILTIN_FUNCTIONS.get(func_name)
            if func is not None:
                try:
                    return func(*args), argc_pos
                except Exception:
                    return None, argc_pos
            return None, argc_pos

        # Parse a value atom
        value = self._parse_atom(tokens, pos, variables)
        return value, pos + 1

    def _parse_atom(
        self, tokens: List[str], pos: int, variables: Dict[str, Any]
    ) -> Any:
        token = tokens[pos]

        # Unary minus for negative numbers
        if token == "-" and pos + 1 < len(tokens):
            next_token = tokens[pos + 1]
            if self._is_number(next_token):
                return -float(next_token) if "." in next_token else -int(next_token)

        # Number literal
        if self._is_number(token):
            return float(token) if "." in token else int(token)

        # String literal
        if (token.startswith('"') and token.endswith('"')) or (
            token.startswith("'") and token.endswith("'")
        ):
            return token[1:-1]

        # Boolean literal
        if token in ("true", "True"):
            return True
        if token in ("false", "False"):
            return False
        if token in ("null", "None"):
            return None

        # Variable reference
        if token in variables:
            return variables[token]
        if token in self._variable_values:
            return self._variable_values[token]

        return 0

    @staticmethod
    def _is_number(token: str) -> bool:
        try:
            float(token)
            return True
        except ValueError:
            return False

    @staticmethod
    def _classify_expression(expr: str) -> ExpressionType:
        expr_lower = expr.strip().lower()
        if expr_lower.startswith("if ") or " then " in expr_lower:
            return ExpressionType.CONDITIONAL
        if expr_lower in ("true", "false") or " and " in expr_lower or " or " in expr_lower:
            return ExpressionType.BOOLEAN
        if any(op in expr for op in (">=", "<=", "!=", "==", ">", "<")):
            return ExpressionType.COMPARISON
        if '"' in expr or "'" in expr:
            return ExpressionType.STRING
        if any(op in expr for op in ("+", "-", "*", "/")):
            return ExpressionType.ARITHMETIC
        if "(" in expr and ")" in expr:
            return ExpressionType.FUNCTION_CALL
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", expr.strip()):
            return ExpressionType.VARIABLE_REF
        return ExpressionType.ARITHMETIC

    @staticmethod
    def _extract_parameters(tokens: List[str]) -> List[str]:
        params: List[str] = []
        seen: set = set()
        reserved = {"and", "or", "not", "if", "then", "else", "true", "false", "null", "None"}
        for token in tokens:
            if token in reserved:
                continue
            if token in _BUILTIN_FUNCTIONS:
                continue
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", token) and token not in seen:
                params.append(token)
                seen.add(token)
        return params


def get_expression_evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator.get_instance()