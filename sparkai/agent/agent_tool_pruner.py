"""
SparkAI Agent - Tool Output Pruning Engine

Systematic pipeline for pruning large tool outputs before they
enter the agent context window. Prevents context overflow by
truncating, summarizing, and structuring tool results.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PruneStrategy(Enum):
    TRUNCATE = "truncate"
    EXTRACT_KEY_FIELDS = "extract_key_fields"
    SUMMARIZE_STRUCTURED = "summarize_structured"
    TAIL_PRESERVE = "tail_preserve"
    HEAD_TAIL_PRESERVE = "head_tail_preserve"


class OutputFormat(Enum):
    TEXT = "text"
    JSON = "json"
    LIST = "list"
    TABLE = "table"
    CODE = "code"
    BINARY = "binary"
    UNKNOWN = "unknown"


@dataclass
class PruneRule:
    tool_name: str
    max_output_chars: int = 4000
    strategy: PruneStrategy = PruneStrategy.TRUNCATE
    key_fields: List[str] = field(default_factory=list)
    preserve_tail_chars: int = 500
    preserve_head_chars: int = 500
    truncate_message: str = "... [output truncated, {original_size} -> {pruned_size} chars]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "max_output_chars": self.max_output_chars,
            "strategy": self.strategy.value,
            "key_fields": self.key_fields,
        }


@dataclass
class PruneResult:
    original_size: int
    pruned_size: int
    strategy_used: PruneStrategy
    was_pruned: bool
    output_format: OutputFormat
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_size": self.original_size,
            "pruned_size": self.pruned_size,
            "strategy_used": self.strategy_used.value,
            "was_pruned": self.was_pruned,
            "output_format": self.output_format.value,
            "reduction_pct": round((1.0 - self.pruned_size / max(self.original_size, 1)) * 100, 1) if self.was_pruned else 0.0,
            "elapsed_ms": self.elapsed_ms,
        }


class ToolOutputPruner:
    """
    Prunes large tool outputs before they enter the agent context.
    Applies configurable rules per tool with multiple strategies.
    """

    DEFAULT_MAX_CHARS = 4000
    ABSOLUTE_MAX_CHARS = 50000

    def __init__(self):
        self._rules: Dict[str, PruneRule] = {}
        self._stats = {
            "total_pruned": 0,
            "total_passed": 0,
            "chars_saved": 0,
            "by_strategy": {},
        }
        self._seed_default_rules()

    def _seed_default_rules(self) -> None:
        defaults = [
            PruneRule(tool_name="read_file", max_output_chars=6000, strategy=PruneStrategy.HEAD_TAIL_PRESERVE, preserve_head_chars=1000, preserve_tail_chars=1000),
            PruneRule(tool_name="list_directory", max_output_chars=3000, strategy=PruneStrategy.TRUNCATE),
            PruneRule(tool_name="search_code", max_output_chars=5000, strategy=PruneStrategy.HEAD_TAIL_PRESERVE, preserve_head_chars=1500, preserve_tail_chars=1000),
            PruneRule(tool_name="execute_command", max_output_chars=6000, strategy=PruneStrategy.TAIL_PRESERVE, preserve_tail_chars=2000),
            PruneRule(tool_name="web_fetch", max_output_chars=8000, strategy=PruneStrategy.HEAD_TAIL_PRESERVE, preserve_head_chars=2000, preserve_tail_chars=2000),
            PruneRule(tool_name="game_build", max_output_chars=4000, strategy=PruneStrategy.EXTRACT_KEY_FIELDS, key_fields=["success", "errors", "warnings", "output_path", "duration"]),
            PruneRule(tool_name="playtest", max_output_chars=4000, strategy=PruneStrategy.EXTRACT_KEY_FIELDS, key_fields=["passed", "scores", "errors", "performance_metrics"]),
            PruneRule(tool_name="validate", max_output_chars=3000, strategy=PruneStrategy.EXTRACT_KEY_FIELDS, key_fields=["valid", "errors", "warnings"]),
            PruneRule(tool_name="generate_code", max_output_chars=10000, strategy=PruneStrategy.HEAD_TAIL_PRESERVE, preserve_head_chars=3000, preserve_tail_chars=3000),
        ]
        for rule in defaults:
            self._rules[rule.tool_name] = rule

    def register_rule(self, rule: PruneRule) -> None:
        self._rules[rule.tool_name] = rule

    def detect_format(self, output: Any) -> OutputFormat:
        if not isinstance(output, str):
            return OutputFormat.BINARY
        stripped = output.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                json.loads(stripped)
                return OutputFormat.JSON
            except json.JSONDecodeError:
                pass
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                json.loads(stripped)
                return OutputFormat.LIST
            except json.JSONDecodeError:
                pass
        if "\n" in stripped and any(kw in stripped for kw in ["function ", "class ", "import ", "def ", "const ", "var "]):
            return OutputFormat.CODE
        if "\t" in stripped or "  " in stripped:
            lines = stripped.split("\n")
            if len(lines) > 2 and all(len(l.split()) >= 3 for l in lines[1:3] if l.strip()):
                return OutputFormat.TABLE
        return OutputFormat.TEXT

    def prune(self, tool_name: str, output: Any) -> tuple:
        start = time.time()
        output_str = str(output) if not isinstance(output, str) else output
        original_size = len(output_str)
        output_format = self.detect_format(output)

        rule = self._rules.get(tool_name)
        max_chars = rule.max_output_chars if rule else self.DEFAULT_MAX_CHARS
        max_chars = min(max_chars, self.ABSOLUTE_MAX_CHARS)

        if original_size <= max_chars:
            elapsed = (time.time() - start) * 1000
            self._stats["total_passed"] += 1
            return output, PruneResult(
                original_size=original_size,
                pruned_size=original_size,
                strategy_used=PruneStrategy.TRUNCATE,
                was_pruned=False,
                output_format=output_format,
                elapsed_ms=elapsed,
            )

        strategy = rule.strategy if rule else PruneStrategy.TRUNCATE
        pruned = self._apply_strategy(strategy, output_str, max_chars, rule, output_format)

        pruned_size = len(pruned)
        elapsed = (time.time() - start) * 1000

        self._stats["total_pruned"] += 1
        self._stats["chars_saved"] += (original_size - pruned_size)
        strat_key = strategy.value
        self._stats["by_strategy"][strat_key] = self._stats["by_strategy"].get(strat_key, 0) + 1

        return pruned, PruneResult(
            original_size=original_size,
            pruned_size=pruned_size,
            strategy_used=strategy,
            was_pruned=True,
            output_format=output_format,
            elapsed_ms=elapsed,
        )

    def _apply_strategy(
        self,
        strategy: PruneStrategy,
        output: str,
        max_chars: int,
        rule: Optional[PruneRule],
        fmt: OutputFormat,
    ) -> str:
        if strategy == PruneStrategy.TRUNCATE:
            return self._truncate(output, max_chars)
        elif strategy == PruneStrategy.HEAD_TAIL_PRESERVE:
            head = rule.preserve_head_chars if rule else 500
            tail = rule.preserve_tail_chars if rule else 500
            return self._head_tail_preserve(output, max_chars, head, tail)
        elif strategy == PruneStrategy.TAIL_PRESERVE:
            tail = rule.preserve_tail_chars if rule else 1000
            return self._tail_preserve(output, max_chars, tail)
        elif strategy == PruneStrategy.EXTRACT_KEY_FIELDS:
            fields = rule.key_fields if rule else []
            return self._extract_key_fields(output, max_chars, fields, fmt)
        elif strategy == PruneStrategy.SUMMARIZE_STRUCTURED:
            return self._summarize_structured(output, max_chars, fmt)
        return self._truncate(output, max_chars)

    def _truncate(self, output: str, max_chars: int) -> str:
        if len(output) <= max_chars:
            return output
        truncation_msg = f"\n... [truncated {len(output)} -> {max_chars} chars]"
        return output[: max_chars - len(truncation_msg)] + truncation_msg

    def _head_tail_preserve(self, output: str, max_chars: int, head: int, tail: int) -> str:
        if len(output) <= max_chars:
            return output
        available = max_chars - 50
        head_size = min(head, available // 2)
        tail_size = min(tail, available - head_size)
        omitted = len(output) - head_size - tail_size
        return (
            output[:head_size]
            + f"\n\n... [{omitted} chars omitted] ...\n\n"
            + output[-tail_size:]
        )

    def _tail_preserve(self, output: str, max_chars: int, tail: int) -> str:
        if len(output) <= max_chars:
            return output
        tail_size = min(tail, max_chars - 50)
        omitted = len(output) - tail_size
        return f"... [{omitted} chars omitted from start] ...\n" + output[-tail_size:]

    def _extract_key_fields(self, output: str, max_chars: int, fields: List[str], fmt: OutputFormat) -> str:
        if fmt in (OutputFormat.JSON, OutputFormat.LIST):
            try:
                data = json.loads(output)
                if isinstance(data, dict):
                    extracted = {k: data[k] for k in fields if k in data}
                    result = json.dumps(extracted, indent=2, default=str)
                    if len(result) <= max_chars:
                        return result
                elif isinstance(data, list):
                    extracted = []
                    for item in data[:10]:
                        if isinstance(item, dict):
                            extracted.append({k: item[k] for k in fields if k in item})
                        else:
                            extracted.append(item)
                    result = json.dumps(extracted, indent=2, default=str)
                    if len(result) <= max_chars:
                        return result
            except (json.JSONDecodeError, TypeError):
                pass

        result_parts = []
        for f in fields:
            for line in output.split("\n"):
                if f.lower() in line.lower():
                    result_parts.append(line.strip())
                    if sum(len(p) for p in result_parts) > max_chars:
                        break
        if result_parts:
            return "\n".join(result_parts)[:max_chars]
        return self._truncate(output, max_chars)

    def _summarize_structured(self, output: str, max_chars: int, fmt: OutputFormat) -> str:
        lines = output.split("\n")
        total_lines = len(lines)
        if total_lines <= 20:
            return self._truncate(output, max_chars)

        first_5 = lines[:5]
        last_5 = lines[-5:]
        summary = (
            first_5
            + [f"... [{total_lines - 10} lines omitted] ..."]
            + last_5
        )
        result = "\n".join(summary)
        if len(result) <= max_chars:
            return result
        return self._truncate(result, max_chars)

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "registered_rules": len(self._rules),
            "default_max_chars": self.DEFAULT_MAX_CHARS,
        }


_global_pruner: Optional[ToolOutputPruner] = None


def get_tool_output_pruner() -> ToolOutputPruner:
    global _global_pruner
    if _global_pruner is None:
        _global_pruner = ToolOutputPruner()
    return _global_pruner


def reset_tool_output_pruner() -> None:
    global _global_pruner
    _global_pruner = None
