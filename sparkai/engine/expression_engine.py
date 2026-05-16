"""
SparkLabs Engine - Expression Engine

Runtime expression parser and evaluator for game scripting, dialogue
conditions, quest triggers, and dynamic content generation. Supports
arithmetic, comparison, logical, and string operations with custom
function registration and variable binding.

Architecture:
  ExpressionEngine
    |-- Tokenizer (lexical analysis into tokens)
    |-- Parser (syntax validation and AST building)
    |-- Evaluator (expression execution with context)
    |-- Function Registry (user-defined callable functions)
    |-- Variable Binder (runtime variable injection)

Supported Operations:
  - Arithmetic: +, -, *, /, %, **
  - Comparison: ==, !=, >, <, >=, <=
  - Logical: &&, ||, !
  - String: ++ (concatenation)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class OperatorType(Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    MODULO = "modulo"
    POWER = "power"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER = "greater"
    LESS = "less"
    GREATER_EQUALS = "greater_equals"
    LESS_EQUALS = "less_equals"
    AND = "and"
    OR = "or"
    NOT = "not"
    CONCATENATE = "concatenate"


OPERATOR_SYMBOLS: Dict[str, OperatorType] = {
    "+": OperatorType.ADD,
    "-": OperatorType.SUBTRACT,
    "*": OperatorType.MULTIPLY,
    "/": OperatorType.DIVIDE,
    "%": OperatorType.MODULO,
    "**": OperatorType.POWER,
    "==": OperatorType.EQUALS,
    "!=": OperatorType.NOT_EQUALS,
    ">": OperatorType.GREATER,
    "<": OperatorType.LESS,
    ">=": OperatorType.GREATER_EQUALS,
    "<=": OperatorType.LESS_EQUALS,
    "&&": OperatorType.AND,
    "||": OperatorType.OR,
    "!": OperatorType.NOT,
    "++": OperatorType.CONCATENATE,
}

OPERATOR_PRECEDENCE: Dict[OperatorType, int] = {
    OperatorType.POWER: 5,
    OperatorType.MULTIPLY: 4,
    OperatorType.DIVIDE: 4,
    OperatorType.MODULO: 4,
    OperatorType.ADD: 3,
    OperatorType.SUBTRACT: 3,
    OperatorType.CONCATENATE: 3,
    OperatorType.EQUALS: 2,
    OperatorType.NOT_EQUALS: 2,
    OperatorType.GREATER: 2,
    OperatorType.LESS: 2,
    OperatorType.GREATER_EQUALS: 2,
    OperatorType.LESS_EQUALS: 2,
    OperatorType.AND: 1,
    OperatorType.OR: 0,
}


@dataclass
class ExpressionToken:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    token_type: str = ""
    value: str = ""
    position: int = 0


@dataclass
class ExpressionContext:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    variables: Dict[str, Any] = field(default_factory=dict)
    functions: Dict[str, Callable] = field(default_factory=dict)
    objects: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpressionResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    expression_text: str = ""
    result: Any = None
    result_type: str = ""
    evaluation_time_ms: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "expression": self.expression_text,
            "result": self.result,
            "result_type": self.result_type,
            "evaluation_time_ms": round(self.evaluation_time_ms, 4),
            "error": self.error_message or None,
        }


class ExpressionEngine:
    """
    Runtime expression parser and evaluator.

    Compiles and executes game expressions with variable substitution
    and custom function support. Used for dialogue conditions,
    quest triggers, combat formulas, and dynamic content.

    Usage:
        engine = get_expression_engine()
        engine.register_function("max", max)
        engine.set_variable("player_level", 5)
        result = engine.execute("player_level * 2 + max(1, 3)", context)
        if result.error_message:
            print(f"Error: {result.error_message}")
    """

    _instance: Optional["ExpressionEngine"] = None

    def __init__(self):
        self._functions: Dict[str, Callable] = {}
        self._variables: Dict[str, Any] = {}
        self._compile_cache: Dict[str, List[ExpressionToken]] = {}
        self._expression_count: int = 0
        self._error_count: int = 0

        self._register_default_functions()

    @classmethod
    def get_instance(cls) -> "ExpressionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_default_functions(self) -> None:
        self._functions["min"] = min
        self._functions["max"] = max
        self._functions["abs"] = abs
        self._functions["round"] = round
        self._functions["len"] = len
        self._functions["int"] = int
        self._functions["float"] = float
        self._functions["str"] = str
        self._functions["bool"] = bool

    def register_function(self, name: str, callable: Callable) -> bool:
        if not callable(name):
            self._functions[name] = callable
            return True
        return False

    def unregister_function(self, name: str) -> bool:
        if name in self._functions and name not in ("min", "max", "abs", "round", "len", "int", "float", "str", "bool"):
            del self._functions[name]
            return True
        return False

    def set_variable(self, name: str, value: Any) -> bool:
        self._variables[name] = value
        return True

    def get_variable(self, name: str) -> Optional[Any]:
        return self._variables.get(name)

    def remove_variable(self, name: str) -> bool:
        if name in self._variables:
            del self._variables[name]
            return True
        return False

    def get_available_functions(self) -> List[str]:
        return sorted(self._functions.keys())

    def compile(self, expression: str) -> bool:
        try:
            tokens = self._tokenize(expression)
            self._validate_tokens(tokens)
            self._compile_cache[expression] = tokens
            return True
        except Exception:
            return False

    def execute(self, expression: str, context: Optional[ExpressionContext] = None) -> ExpressionResult:
        self._expression_count += 1
        start_time = time.time()

        result = ExpressionResult(expression_text=expression)

        try:
            if context is None:
                context = ExpressionContext(variables=dict(self._variables), functions=dict(self._functions))

            merged_vars = dict(self._variables)
            merged_vars.update(context.variables)
            merged_funcs = dict(self._functions)
            merged_funcs.update(context.functions)

            tokens = self._compile_cache.get(expression)
            if tokens is None:
                tokens = self._tokenize(expression)
                self._validate_tokens(tokens)

            value = self._evaluate_tokens(tokens, merged_vars, merged_funcs)

            result.result = value
            result.result_type = type(value).__name__
        except Exception as e:
            self._error_count += 1
            result.result = None
            result.result_type = "error"
            result.error_message = str(e)

        result.evaluation_time_ms = (time.time() - start_time) * 1000.0
        return result

    def validate_syntax(self, expression: str) -> List[str]:
        errors: List[str] = []
        try:
            tokens = self._tokenize(expression)
            self._validate_tokens(tokens)
        except Exception as e:
            errors.append(str(e))

        paren_count = 0
        for ch in expression:
            if ch == "(":
                paren_count += 1
            elif ch == ")":
                paren_count -= 1
            if paren_count < 0:
                errors.append("Unmatched closing parenthesis")
                break
        if paren_count > 0:
            errors.append("Unmatched opening parenthesis")

        return errors

    def _tokenize(self, expression: str) -> List[ExpressionToken]:
        tokens: List[ExpressionToken] = []
        i = 0
        n = len(expression)

        while i < n:
            ch = expression[i]

            if ch.isspace():
                i += 1
                continue

            if ch.isdigit() or (ch == "." and i + 1 < n and expression[i + 1].isdigit()):
                start = i
                has_dot = ch == "."
                i += 1
                while i < n and (expression[i].isdigit() or (expression[i] == "." and not has_dot)):
                    if expression[i] == ".":
                        has_dot = True
                    i += 1
                tokens.append(ExpressionToken(token_type="number", value=expression[start:i], position=start))
                continue

            if ch.isalpha() or ch == "_":
                start = i
                i += 1
                while i < n and (expression[i].isalnum() or expression[i] == "_"):
                    i += 1
                word = expression[start:i]
                if word in ("true", "false"):
                    tokens.append(ExpressionToken(token_type="boolean", value=word, position=start))
                elif word == "null":
                    tokens.append(ExpressionToken(token_type="null", value=word, position=start))
                else:
                    tokens.append(ExpressionToken(token_type="identifier", value=word, position=start))
                continue

            if ch in ('"', "'"):
                quote = ch
                start = i
                i += 1
                while i < n and expression[i] != quote:
                    if expression[i] == "\\" and i + 1 < n:
                        i += 1
                    i += 1
                i += 1
                tokens.append(ExpressionToken(token_type="string", value=expression[start:i], position=start))
                continue

            two_char = expression[i : i + 2]
            if two_char in OPERATOR_SYMBOLS:
                tokens.append(ExpressionToken(token_type="operator", value=two_char, position=i))
                i += 2
                continue

            if ch in OPERATOR_SYMBOLS:
                tokens.append(ExpressionToken(token_type="operator", value=ch, position=i))
                i += 1
                continue

            if ch in ("(", ")", ","):
                tokens.append(ExpressionToken(token_type="delimiter", value=ch, position=i))
                i += 1
                continue

            raise ValueError(f"Unexpected character '{ch}' at position {i}")

        return tokens

    def _validate_tokens(self, tokens: List[ExpressionToken]) -> None:
        if not tokens:
            raise ValueError("Empty expression")

    def _evaluate_tokens(
        self,
        tokens: List[ExpressionToken],
        variables: Dict[str, Any],
        functions: Dict[str, Callable],
    ) -> Any:
        output: List[Any] = []
        operators: List[ExpressionToken] = []

        def apply_operator() -> None:
            if not operators:
                return
            op_token = operators.pop()
            op_type = OPERATOR_SYMBOLS.get(op_token.value)

            if op_type == OperatorType.NOT:
                a = output.pop()
                output.append(not a)
                return

            if len(output) < 2:
                raise ValueError(f"Not enough operands for operator '{op_token.value}'")
            b = output.pop()
            a = output.pop()

            op_map: Dict[OperatorType, Any] = {
                OperatorType.ADD: lambda x, y: x + y,
                OperatorType.SUBTRACT: lambda x, y: x - y,
                OperatorType.MULTIPLY: lambda x, y: x * y,
                OperatorType.DIVIDE: lambda x, y: x / y,
                OperatorType.MODULO: lambda x, y: x % y,
                OperatorType.POWER: lambda x, y: x ** y,
                OperatorType.EQUALS: lambda x, y: x == y,
                OperatorType.NOT_EQUALS: lambda x, y: x != y,
                OperatorType.GREATER: lambda x, y: x > y,
                OperatorType.LESS: lambda x, y: x < y,
                OperatorType.GREATER_EQUALS: lambda x, y: x >= y,
                OperatorType.LESS_EQUALS: lambda x, y: x <= y,
                OperatorType.AND: lambda x, y: bool(x) and bool(y),
                OperatorType.OR: lambda x, y: bool(x) or bool(y),
                OperatorType.CONCATENATE: lambda x, y: str(x) + str(y),
            }

            fn = op_map.get(op_type)
            if fn is None:
                raise ValueError(f"Unknown operator '{op_token.value}'")
            output.append(fn(a, b))

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.token_type == "number":
                value = token.value
                output.append(float(value) if "." in value else int(value))

            elif token.token_type == "string":
                raw = token.value
                output.append(raw[1:-1])

            elif token.token_type == "boolean":
                output.append(token.value == "true")

            elif token.token_type == "null":
                output.append(None)

            elif token.token_type == "identifier":
                if i + 1 < len(tokens) and tokens[i + 1].value == "(":
                    func_name = token.value
                    if func_name not in functions:
                        raise ValueError(f"Unknown function '{func_name}'")
                    i += 1
                    args: List[Any] = []
                    paren_count = 1
                    arg_start = i + 1
                    arg_tokens: List[ExpressionToken] = []
                    i += 1
                    while i < len(tokens) and paren_count > 0:
                        t = tokens[i]
                        if t.value == "(":
                            paren_count += 1
                        elif t.value == ")":
                            paren_count -= 1
                            if paren_count == 0:
                                if arg_tokens:
                                    args.append(self._evaluate_tokens(arg_tokens, variables, functions))
                                break
                        elif t.value == "," and paren_count == 1:
                            if arg_tokens:
                                args.append(self._evaluate_tokens(arg_tokens, variables, functions))
                            arg_tokens = []
                            i += 1
                            continue
                        if paren_count > 0:
                            arg_tokens.append(t)
                        i += 1
                    if paren_count != 0:
                        raise ValueError(f"Mismatched parentheses in function call '{func_name}'")
                    output.append(functions[func_name](*args))
                else:
                    if token.value in variables:
                        output.append(variables[token.value])
                    else:
                        raise ValueError(f"Undefined variable '{token.value}'")

            elif token.token_type == "operator":
                op_type = OPERATOR_SYMBOLS.get(token.value)
                if op_type is None:
                    raise ValueError(f"Unknown operator '{token.value}'")
                precedence = OPERATOR_PRECEDENCE.get(op_type, -1)
                while operators and operators[-1].value != "(":
                    top_type = OPERATOR_SYMBOLS.get(operators[-1].value)
                    if top_type and OPERATOR_PRECEDENCE.get(top_type, -1) >= precedence:
                        apply_operator()
                    else:
                        break
                operators.append(token)

            elif token.value == "(":
                operators.append(token)

            elif token.value == ")":
                while operators and operators[-1].value != "(":
                    apply_operator()
                if operators and operators[-1].value == "(":
                    operators.pop()
                else:
                    raise ValueError("Mismatched parentheses")

            i += 1

        while operators:
            apply_operator()

        if len(output) != 1:
            raise ValueError(f"Expression evaluation produced {len(output)} results, expected 1")

        return output[0]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "expression_count": self._expression_count,
            "error_count": self._error_count,
            "function_count": len(self._functions),
            "variable_count": len(self._variables),
            "cache_size": len(self._compile_cache),
            "available_functions": self.get_available_functions(),
        }

    def reset(self) -> None:
        self._variables.clear()
        self._compile_cache.clear()
        self._expression_count = 0
        self._error_count = 0


def get_expression_engine() -> ExpressionEngine:
    return ExpressionEngine.get_instance()