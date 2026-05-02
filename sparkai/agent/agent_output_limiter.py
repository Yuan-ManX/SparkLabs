"""
Output Limiter - Constrains and sanitizes agent outputs for UI-safe rendering.

Architecture:
    OutputLimiter/
    |-- LimitPolicy (truncation strategy enumeration)
    |-- LimitRule (per-type constraints dataclass)
    |-- LimitedOutput (processed result dataclass)
    |-- OutputLimiter (global output control)

Controls the size, format, and safety of agent-produced content before
it reaches the game editor UI. Prevents UI freezing from oversized tool
results, truncates long text with context preservation, and ensures
binary/image content is filtered for editor-safe display.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class LimitPolicy(Enum):
    TRUNCATE_HEAD = auto()
    TRUNCATE_TAIL = auto()
    TRUNCATE_SIDES = auto()
    REJECT = auto()
    PASS_THROUGH = auto()


@dataclass
class LimitRule:
    content_type: str = "text"
    max_chars: int = 50000
    max_lines: int = 1000
    max_depth: int = 10
    policy: LimitPolicy = LimitPolicy.TRUNCATE_TAIL
    strip_binary: bool = True
    strip_html: bool = False
    allowed_tags: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type,
            "max_chars": self.max_chars,
            "max_lines": self.max_lines,
            "policy": self.policy.name,
            "strip_binary": self.strip_binary,
            "strip_html": self.strip_html,
        }


@dataclass
class LimitedOutput:
    original_size: int = 0
    limited_size: int = 0
    was_limited: bool = False
    policy_applied: LimitPolicy = LimitPolicy.PASS_THROUGH
    content: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_size": self.original_size,
            "limited_size": self.limited_size,
            "was_limited": self.was_limited,
            "policy": self.policy_applied.name,
            "content": self.content,
            "warnings": self.warnings,
        }


class OutputLimiter:
    _instance: Optional["OutputLimiter"] = None
    _BINARY_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')

    def __init__(self):
        self._rules: Dict[str, LimitRule] = {}
        self._total_limited: int = 0
        self._total_rejected: int = 0
        self._total_bytes_saved: int = 0
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        self._rules["text"] = LimitRule(
            content_type="text",
            max_chars=50000,
            max_lines=1000,
            policy=LimitPolicy.TRUNCATE_TAIL,
        )
        self._rules["code"] = LimitRule(
            content_type="code",
            max_chars=100000,
            max_lines=2000,
            policy=LimitPolicy.TRUNCATE_TAIL,
        )
        self._rules["json"] = LimitRule(
            content_type="json",
            max_chars=200000,
            max_depth=20,
            policy=LimitPolicy.TRUNCATE_SIDES,
        )
        self._rules["html"] = LimitRule(
            content_type="html",
            max_chars=30000,
            strip_html=False,
            policy=LimitPolicy.TRUNCATE_TAIL,
            allowed_tags={"b", "i", "u", "code", "pre", "p", "br", "ul", "ol", "li"},
        )
        self._rules["binary"] = LimitRule(
            content_type="binary",
            max_chars=0,
            policy=LimitPolicy.REJECT,
            strip_binary=True,
        )
        self._rules["default"] = LimitRule(
            content_type="default",
            max_chars=20000,
            max_lines=500,
            policy=LimitPolicy.TRUNCATE_TAIL,
        )

    @classmethod
    def get_instance(cls) -> "OutputLimiter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_rule(self, rule: LimitRule) -> None:
        self._rules[rule.content_type] = rule

    def get_rule(self, content_type: str) -> LimitRule:
        return self._rules.get(content_type, self._rules["default"])

    def limit(self, content: str, content_type: str = "text") -> LimitedOutput:
        rule = self.get_rule(content_type)
        original_size = len(content)
        output = LimitedOutput(original_size=original_size)

        if rule.policy == LimitPolicy.REJECT:
            self._total_rejected += 1
            output.was_limited = True
            output.policy_applied = LimitPolicy.REJECT
            output.content = f"[Content of type '{content_type}' rejected by output policy]"
            output.limited_size = len(output.content)
            return output

        if rule.strip_binary and self._contains_binary(content):
            content = self._strip_binary(content)
            output.warnings.append("Binary content removed")

        if rule.strip_html:
            content = self._strip_html_tags(content, rule.allowed_tags)
            output.warnings.append("HTML tags stripped")

        if rule.max_lines > 0:
            lines = content.split("\n")
            if len(lines) > rule.max_lines:
                content = self._apply_truncation(
                    "\n".join(lines), rule.max_chars, rule.policy
                )
                output.warnings.append(
                    f"Truncated from {len(lines)} to {rule.max_lines} lines"
                )

        if len(content) > rule.max_chars:
            content = self._apply_truncation(content, rule.max_chars, rule.policy)
            bytes_saved = original_size - len(content)
            self._total_bytes_saved += bytes_saved
            output.warnings.append(
                f"Truncated from {original_size} to {len(content)} chars"
            )

        output.content = content
        output.limited_size = len(content)
        output.was_limited = original_size != len(content)
        if output.was_limited:
            output.policy_applied = rule.policy
            self._total_limited += 1

        return output

    def limit_dict(self, data: Dict[str, Any], content_type: str = "json",
                   max_depth: Optional[int] = None) -> Dict[str, Any]:
        rule = self.get_rule(content_type)
        depth = max_depth or rule.max_depth
        return self._truncate_dict(data, depth, 0)

    def _apply_truncation(self, content: str, max_chars: int, policy: LimitPolicy) -> str:
        if len(content) <= max_chars:
            return content

        if policy == LimitPolicy.TRUNCATE_HEAD:
            cutoff = min(max(0, len(content) - max_chars + 20), len(content))
            return f"...[truncated]...{content[cutoff:]}"
        elif policy == LimitPolicy.TRUNCATE_SIDES:
            half = max_chars // 2 - 10
            return f"{content[:half]}\n...[truncated {len(content) - max_chars} chars]...\n{content[-half:]}"
        else:
            return f"{content[:max_chars - 20]}...[truncated]"

    def _contains_binary(self, content: str) -> bool:
        if not content:
            return False
        binary_count = len(self._BINARY_PATTERN.findall(content[:10000]))
        return binary_count > len(content[:10000]) * 0.05

    def _strip_binary(self, content: str) -> str:
        return self._BINARY_PATTERN.sub('', content)

    def _strip_html_tags(self, content: str, allowed: Set[str]) -> str:
        if not allowed:
            return re.sub(r'<[^>]+>', '', content)
        pattern = r'<(?!\/?(?:' + '|'.join(re.escape(t) for t in allowed) + r')\b)[^>]+>'
        return re.sub(pattern, '', content)

    def _truncate_dict(self, data: Dict[str, Any], max_depth: int, current_depth: int) -> Dict[str, Any]:
        if current_depth >= max_depth:
            return {"_truncated": f"Max depth {max_depth} reached"}
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._truncate_dict(value, max_depth, current_depth + 1)
            elif isinstance(value, list) and len(value) > 100:
                result[key] = value[:100] + [f"... {len(value) - 100} more items"]
            elif isinstance(value, str) and len(value) > 10000:
                result[key] = value[:10000] + "..."
            else:
                result[key] = value
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_limited": self._total_limited,
            "total_rejected": self._total_rejected,
            "total_bytes_saved": self._total_bytes_saved,
            "rules_count": len(self._rules),
            "rules": {k: v.to_dict() for k, v in self._rules.items()},
        }


def get_output_limiter() -> OutputLimiter:
    return OutputLimiter.get_instance()
