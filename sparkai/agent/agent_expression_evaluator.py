"""
SparkLabs Agent - Expression Evaluator

Expression evaluation engine for game logic conditions, mathematical
computations, and string operations. Powers the event system's
condition checking, variable computations, and dynamic game rules.
Provides safe evaluation with configurable operator and function sets.

Architecture:
  ExpressionEvaluator
    |-- Tokenizer (lexer: numbers, operators, identifiers, parens)
    |-- Parser (recursive descent AST builder)
    |-- Evaluator (AST walker with scoped variable resolution)
    |-- FunctionRegistry (pluggable functions: sin, cos, random, clamp)
    |-- SecuritySandbox (forbidden operations, recursion depth limit)

Expression Types:
  - MATH: "score * 1.5 + bonus"
  - LOGIC: "health > 0 && ammo >= 1"
  - STRING: "Player: " + player_name
  - MIXED: ternary, type coercion

Operator Precedence (low to high):
  1. Assignment (=)
  2. Logical OR (||)
  3. Logical AND (&&)
  4. Comparison (==, !=, <, >, <=, >=)
  5. Addition/Subtraction (+, -)
  6. Multiplication/Division (*, /, %)
  7. Unary (!, -)
  8. Function call, Member access (.)
"""

from __future__ import annotations

import math
import operator
import random as _random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class TokenType(Enum):
    NUMBER = "number"
    STRING = "string"
    IDENTIFIER = "identifier"
    OPERATOR = "operator"
    LPAREN = "lparen"
    RPAREN = "rparen"
    COMMA = "comma"
    DOT = "dot"
    EOF = "eof"


@dataclass
class Token:
    token_type: TokenType
    value: str
    position: int = 0


class ExpressionError(Exception):
    pass


class ExpressionEvaluator:
    """
    Safe expression evaluator for game logic.

    Evaluates mathematical, logical, and string expressions
    with scoped variable resolution. Powers the event system's
    condition checking, variable computations, and dynamic
    game rules. AI agents generate expressions for game events
    and this evaluator ensures they execute safely.
    """

    _instance: Optional["ExpressionEvaluator"] = None

    PRECEDENCE: Dict[str, int] = {
        "=": 1,
        "||": 2,
        "&&": 3,
        "==": 4,
        "!=": 4,
        "<": 4,
        ">": 4,
        "<=": 4,
        ">=": 4,
        "+": 5,
        "-": 5,
        "*": 6,
        "/": 6,
        "%": 6,
        "!": 7,
    }

    RIGHT_ASSOCIATIVE: set = {"=", "!"}

    def __init__(self):
        self._functions: Dict[str, Callable] = {
            "abs": abs,
            "min": min,
            "max": max,
            "floor": math.floor,
            "ceil": math.ceil,
            "round": round,
            "sqrt": math.sqrt,
            "pow": pow,
            "sin": math.sin,
            "cos": math.cos,
            "random": lambda: _random.random(),
            "randint": lambda a, b: _random.randint(int(a), int(b)),
            "clamp": lambda v, lo, hi: max(lo, min(hi, v)),
            "len": len,
            "str": str,
            "int": lambda x: int(float(x)),
            "float": float,
            "bool": bool,
            "typeof": lambda x: type(x).__name__,
        }
        self._max_depth: int = 50
        self._max_string_length: int = 1000

    @classmethod
    def get_instance(cls) -> "ExpressionEvaluator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_function(self, name: str, fn: Callable) -> None:
        self._functions[name] = fn

    def evaluate(
        self, expression: str, variables: Optional[Dict[str, Any]] = None
    ) -> Any:
        if not expression or not expression.strip():
            return None
        tokens = self._tokenize(expression)
        if not tokens:
            return None
        ast = self._parse(tokens)
        result = self._eval_node(ast, variables or {}, 0)
        if isinstance(result, str) and len(result) > self._max_string_length:
            result = result[: self._max_string_length]
        return result

    def evaluate_bool(
        self, expression: str, variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        result = self.evaluate(expression, variables)
        return bool(result)

    def evaluate_number(
        self, expression: str, variables: Optional[Dict[str, Any]] = None
    ) -> float:
        result = self.evaluate(expression, variables)
        try:
            return float(result)
        except (TypeError, ValueError):
            return 0.0

    def validate(self, expression: str) -> tuple[bool, str]:
        try:
            self._tokenize(expression)
            return True, "valid"
        except ExpressionError as e:
            return False, str(e)

    def _tokenize(self, expression: str) -> List[Token]:
        tokens: List[Token] = []
        i = 0
        n = len(expression)

        while i < n:
            ch = expression[i]

            if ch.isspace():
                i += 1
                continue

            if ch.isdigit() or (ch == "." and i + 1 < n and expression[i + 1].isdigit()):
                start = i
                dots = 0
                while i < n and (expression[i].isdigit() or expression[i] == "."):
                    if expression[i] == ".":
                        dots += 1
                        if dots > 1:
                            break
                    i += 1
                tokens.append(Token(TokenType.NUMBER, expression[start:i], start))
                continue

            if ch in ('"', "'"):
                quote = ch
                i += 1
                start = i
                while i < n and expression[i] != quote:
                    if expression[i] == "\\" and i + 1 < n:
                        i += 2
                    else:
                        i += 1
                if i >= n:
                    raise ExpressionError(f"Unterminated string at position {start}")
                val = expression[start:i]
                i += 1
                tokens.append(Token(TokenType.STRING, val, start))
                continue

            if ch.isalpha() or ch == "_":
                start = i
                while i < n and (expression[i].isalnum() or expression[i] == "_"):
                    i += 1
                tokens.append(
                    Token(TokenType.IDENTIFIER, expression[start:i], start)
                )
                continue

            if ch == "(":
                tokens.append(Token(TokenType.LPAREN, "(", i))
            elif ch == ")":
                tokens.append(Token(TokenType.RPAREN, ")", i))
            elif ch == ",":
                tokens.append(Token(TokenType.COMMA, ",", i))
            elif ch == ".":
                tokens.append(Token(TokenType.DOT, ".", i))
            elif ch in ("+", "-", "*", "/", "%"):
                tokens.append(Token(TokenType.OPERATOR, ch, i))
            elif ch == "!" and i + 1 < n and expression[i + 1] == "=":
                tokens.append(Token(TokenType.OPERATOR, "!=", i))
                i += 1
            elif ch == "=" and i + 1 < n and expression[i + 1] == "=":
                tokens.append(Token(TokenType.OPERATOR, "==", i))
                i += 1
            elif ch == "=":
                tokens.append(Token(TokenType.OPERATOR, "=", i))
            elif ch == "<" and i + 1 < n and expression[i + 1] == "=":
                tokens.append(Token(TokenType.OPERATOR, "<=", i))
                i += 1
            elif ch == ">" and i + 1 < n and expression[i + 1] == "=":
                tokens.append(Token(TokenType.OPERATOR, ">=", i))
                i += 1
            elif ch in ("<", ">"):
                tokens.append(Token(TokenType.OPERATOR, ch, i))
            elif ch == "&" and i + 1 < n and expression[i + 1] == "&":
                tokens.append(Token(TokenType.OPERATOR, "&&", i))
                i += 1
            elif ch == "|" and i + 1 < n and expression[i + 1] == "|":
                tokens.append(Token(TokenType.OPERATOR, "||", i))
                i += 1
            elif ch == "!":
                tokens.append(Token(TokenType.OPERATOR, "!", i))
            else:
                raise ExpressionError(f"Unexpected character '{ch}' at position {i}")

            i += 1

        tokens.append(Token(TokenType.EOF, "", n))
        return tokens

    def _parse(self, tokens: List[Token]) -> dict:
        self._pos = 0
        self._tokens = tokens
        node = self._parse_expression(0)
        if self._current().token_type != TokenType.EOF:
            raise ExpressionError(
                f"Unexpected token '{self._current().value}' at position {self._current().position}"
            )
        return node

    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.token_type != TokenType.EOF:
            self._pos += 1
        return tok

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _expect(self, token_type: TokenType) -> Token:
        tok = self._advance()
        if tok.token_type != token_type:
            raise ExpressionError(
                f"Expected {token_type.value} but got '{tok.value}' at position {tok.position}"
            )
        return tok

    def _parse_expression(self, min_prec: int = 0) -> dict:
        tok = self._current()

        if tok.token_type == TokenType.IDENTIFIER:
            ident = self._advance()
            lookahead = self._current()
            if lookahead.token_type == TokenType.LPAREN:
                node = self._parse_function_call(ident.value)
            else:
                node = {"type": "identifier", "name": ident.value}
        elif tok.token_type == TokenType.NUMBER:
            val = float(self._advance().value)
            node = {"type": "number", "value": val}
        elif tok.token_type == TokenType.STRING:
            node = {"type": "string", "value": self._advance().value}
        elif tok.token_type == TokenType.OPERATOR and tok.value == "-":
            self._advance()
            operand = self._parse_expression(self.PRECEDENCE.get("!", 7))
            node = {"type": "unary", "operator": "-", "operand": operand}
        elif tok.token_type == TokenType.OPERATOR and tok.value == "!":
            self._advance()
            operand = self._parse_expression(self.PRECEDENCE.get("!", 7))
            node = {"type": "unary", "operator": "!", "operand": operand}
        elif tok.token_type == TokenType.LPAREN:
            self._advance()
            node = self._parse_expression(0)
            self._expect(TokenType.RPAREN)
        else:
            raise ExpressionError(
                f"Unexpected token '{tok.value}' at position {tok.position}"
            )

        while True:
            op_tok = self._current()
            if op_tok.token_type != TokenType.OPERATOR:
                break
            op_prec = self.PRECEDENCE.get(op_tok.value, -1)
            if op_prec < min_prec:
                break
            is_right = op_tok.value in self.RIGHT_ASSOCIATIVE
            next_min = op_prec if is_right else op_prec + 1
            self._advance()
            rhs = self._parse_expression(next_min)
            node = {"type": "binary", "operator": op_tok.value, "left": node, "right": rhs}

        return node

    def _parse_function_call(self, name: str) -> dict:
        self._advance()
        args = []
        if self._current().token_type != TokenType.RPAREN:
            args.append(self._parse_expression(0))
            while self._current().token_type == TokenType.COMMA:
                self._advance()
                args.append(self._parse_expression(0))
        self._expect(TokenType.RPAREN)
        return {"type": "function", "name": name, "arguments": args}

    def _eval_node(self, node: dict, variables: Dict[str, Any], depth: int) -> Any:
        if depth > self._max_depth:
            raise ExpressionError("Maximum expression recursion depth exceeded")

        ntype = node["type"]

        if ntype == "number":
            return node["value"]
        elif ntype == "string":
            return node["value"]
        elif ntype == "identifier":
            name = node["name"]
            if name in variables:
                return variables[name]
            if name in ("true", "True"):
                return True
            if name in ("false", "False"):
                return False
            if name in ("null", "None"):
                return None
            return name
        elif ntype == "unary":
            op = node["operator"]
            val = self._eval_node(node["operand"], variables, depth + 1)
            if op == "-":
                return -float(val)
            elif op == "!":
                return not bool(val)
        elif ntype == "binary":
            left = self._eval_node(node["left"], variables, depth + 1)
            op = node["operator"]
            if op == "&&":
                if not bool(left):
                    return False
                return bool(self._eval_node(node["right"], variables, depth + 1))
            if op == "||":
                if bool(left):
                    return True
                return bool(self._eval_node(node["right"], variables, depth + 1))
            right = self._eval_node(node["right"], variables, depth + 1)
            ops: Dict[str, Callable] = {
                "+": lambda a, b: (
                    str(a) + str(b)
                    if isinstance(a, str) or isinstance(b, str)
                    else float(a) + float(b)
                ),
                "-": lambda a, b: float(a) - float(b),
                "*": lambda a, b: float(a) * float(b),
                "/": lambda a, b: float(a) / float(b) if float(b) != 0 else 0.0,
                "%": lambda a, b: float(a) % float(b) if float(b) != 0 else 0.0,
                "==": lambda a, b: a == b,
                "!=": lambda a, b: a != b,
                "<": lambda a, b: float(a) < float(b),
                ">": lambda a, b: float(a) > float(b),
                "<=": lambda a, b: float(a) <= float(b),
                ">=": lambda a, b: float(a) >= float(b),
                "=": lambda a, b: b,
            }
            if op in ops:
                return ops[op](left, right)
        elif ntype == "function":
            name = node["name"]
            fn = self._functions.get(name)
            if not fn:
                raise ExpressionError(f"Unknown function '{name}'")
            args = [self._eval_node(a, variables, depth + 1) for a in node["arguments"]]
            try:
                return fn(*args)
            except Exception as e:
                raise ExpressionError(f"Function '{name}' error: {e}")

        raise ExpressionError(f"Unknown node type: {ntype}")

    def get_stats(self) -> dict:
        return {
            "registered_functions": len(self._functions),
            "max_depth": self._max_depth,
            "max_string_length": self._max_string_length,
        }

    def reset(self) -> None:
        pass


def get_expression_evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator.get_instance()
