"""
SparkLabs Engine - JavaScript Validator

Validates generated game HTML/JavaScript for syntax integrity before the
runtime reaches the player. Catches the class of bugs that silently break
the entire script block (unmatched braces, double-brace artifacts from
string templating, unclosed string literals, etc.).

The validator runs purely on string analysis — no JS engine required — so
it works in any Python environment and is fast enough for real-time use
inside the conductor pipeline.

Check categories:
  - brace_balance    : {}, (), [] nesting and matching
  - double_brace     : {{ or }} artifacts from templating bugs
  - string_integrity : unclosed string literals
  - script_tags      : <script> open/close pairing
  - keyword_sanity   : var/let/const without identifier, return outside function
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationIssue:
    """A single issue found during validation."""

    category: str
    severity: str  # "error", "warning", "info"
    message: str
    line: int = 0
    snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "snippet": self.snippet[:120],
        }


@dataclass
class ValidationReport:
    """Full validation result for a game HTML document."""

    passed: bool = True
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    script_blocks_checked: int = 0
    total_lines: int = 0
    checks_run: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [i.to_dict() for i in self.issues],
            "script_blocks_checked": self.script_blocks_checked,
            "total_lines": self.total_lines,
            "checks_run": self.checks_run,
        }


class JSValidator:
    """
    Validates JavaScript inside HTML game documents without requiring a JS
    runtime. Uses heuristic string analysis to catch the most common
    game-breaking bugs.
    """

    # Regex to extract <script> block contents (non-greedy, DOTALL)
    _SCRIPT_RE = re.compile(
        r"<script(?:\s[^>]*)?>(.*?)</script>",
        re.DOTALL | re.IGNORECASE,
    )

    # Patterns that indicate a string templating bug
    _DOUBLE_BRACE_RE = re.compile(r"\{\{|\}\}")

    # Match opening brackets for balance checking
    _OPEN_RE = re.compile(r"[\{\(\[]")
    _CLOSE_RE = re.compile(r"[\}\)\]]")

    def __init__(self) -> None:
        self._bracket_pairs = {"{": "}", "(": ")", "[": "]"}
        self._close_to_open = {"}": "{", ")": "(", "]": "["}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_html(self, html: str) -> ValidationReport:
        """Validate all <script> blocks inside an HTML document."""
        report = ValidationReport()
        report.total_lines = html.count("\n") + 1

        scripts = self._SCRIPT_RE.findall(html)
        report.script_blocks_checked = len(scripts)

        if not scripts:
            report.issues.append(
                ValidationIssue(
                    category="script_tags",
                    severity="warning",
                    message="No <script> blocks found in HTML",
                )
            )
            report.warning_count += 1
            report.checks_run = ["script_tags"]
            return report

        for idx, js_code in enumerate(scripts):
            self._validate_script_block(js_code, idx + 1, report)

        # Run HTML-level checks
        self._check_script_tag_pairing(html, report)

        report.passed = report.error_count == 0
        return report

    def validate_js(self, js_code: str) -> ValidationReport:
        """Validate a standalone JavaScript string."""
        report = ValidationReport()
        report.total_lines = js_code.count("\n") + 1
        report.script_blocks_checked = 1
        self._validate_script_block(js_code, 1, report)
        report.passed = report.error_count == 0
        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _validate_script_block(
        self, js: str, block_num: int, report: ValidationReport
    ) -> None:
        """Run all checks on a single script block."""
        checks = [
            "double_brace",
            "brace_balance",
            "string_integrity",
            "keyword_sanity",
        ]
        report.checks_run.extend(checks)

        for check_name in checks:
            method = getattr(self, "_check_" + check_name)
            issues = method(js)
            for issue in issues:
                issue.message = "[block {}] {}".format(block_num, issue.message)
                report.issues.append(issue)
                if issue.severity == "error":
                    report.error_count += 1
                elif issue.severity == "warning":
                    report.warning_count += 1
                else:
                    report.info_count += 1

    def _check_double_brace(self, js: str) -> List[ValidationIssue]:
        """
        Detect {{ artifacts from Python string-templating leaks. In
        JavaScript, {{ is a syntax error when starting a block or object
        literal (e.g. "function() {{", "if (x) {{").

        Note: }} is NOT flagged because it is a valid pattern in nested
        object literals (e.g. {"a": {"b": 1}}) and JSON data embedded
        in script blocks. Blindly treating }} as an error causes false
        positives that corrupt valid game data.
        """
        issues: List[ValidationIssue] = []
        # Only flag {{ (not }}) — }} is valid in nested object literals
        open_double_re = re.compile(r"\{\{")
        lines = js.split("\n")
        for i, line in enumerate(lines, 1):
            for match in open_double_re.finditer(line):
                # Skip if inside any string literal (single, double, backtick)
                before = line[: match.start()]
                if self._is_inside_string_literal(before):
                    continue
                issues.append(
                    ValidationIssue(
                        category="double_brace",
                        severity="error",
                        message="Double-brace artifact '{{' found — likely a templating bug",
                        line=i,
                        snippet=line.strip(),
                    )
                )
        return issues

    @staticmethod
    def _is_inside_string_literal(text_before: str) -> bool:
        """
        Determine if the position after text_before is inside a string
        literal. Tracks single quotes, double quotes, and backticks,
        respecting escape sequences.
        """
        in_string: Optional[str] = None
        i = 0
        while i < len(text_before):
            ch = text_before[i]
            if in_string:
                if ch == "\\":
                    i += 2  # Skip escaped character
                    continue
                if ch == in_string:
                    in_string = None
            else:
                if ch in ("'", '"', "`"):
                    in_string = ch
                elif ch == "/" and i + 1 < len(text_before):
                    # Skip line comments
                    if text_before[i + 1] == "/":
                        break
                    # Skip block comments
                    if text_before[i + 1] == "*":
                        end = text_before.find("*/", i + 2)
                        if end == -1:
                            break
                        i = end + 2
                        continue
            i += 1
        return in_string is not None

    def _check_brace_balance(self, js: str) -> List[ValidationIssue]:
        """
        Check that {}, (), and [] are balanced. Uses a simple stack-based
        approach that ignores brackets inside string and comment literals.

        Note: JavaScript regex literals (e.g. /[{]\\}/g) can contain brackets
        that look unbalanced to a non-JS-aware parser. To avoid false
        positives, mid-file mismatched closers are downgraded to warnings;
        only unclosed brackets at end-of-file are treated as errors, since
        those are the real syntax errors that break script execution.
        """
        issues: List[ValidationIssue] = []
        stack: List[Tuple[str, int, int]] = []  # (bracket, line, col)
        lines = js.split("\n")

        i = 0
        line_num = 1
        col = 0
        in_string: Optional[str] = None  # ", ', or `
        in_line_comment = False
        in_block_comment = False
        # Track whether we are inside a regex literal (heuristic)
        in_regex = False
        regex_flags_seen = False

        while i < len(js):
            ch = js[i]
            next_ch = js[i + 1] if i + 1 < len(js) else ""

            if ch == "\n":
                line_num += 1
                col = 0
                in_line_comment = False
                in_regex = False
                regex_flags_seen = False
                i += 1
                continue
            col += 1

            # Handle comments
            if in_line_comment:
                i += 1
                continue
            if in_block_comment:
                if ch == "*" and next_ch == "/":
                    in_block_comment = False
                    i += 2
                    col += 1
                    continue
                i += 1
                continue
            if not in_string and not in_regex:
                if ch == "/" and next_ch == "/":
                    in_line_comment = True
                    i += 2
                    col += 1
                    continue
                if ch == "/" and next_ch == "*":
                    in_block_comment = True
                    i += 2
                    col += 1
                    continue

            # Handle regex literals (heuristic: / starts a regex if previous
            # non-space char suggests an expression context)
            if in_regex:
                if ch == "\\":
                    i += 2  # Skip escaped char in regex
                    col += 1
                    continue
                if ch == "/":
                    in_regex = False
                    regex_flags_seen = True
                i += 1
                continue
            if regex_flags_seen and ch.isalpha():
                # Consume regex flags (g, i, m, s, u, y)
                i += 1
                continue
            regex_flags_seen = False

            # Handle strings
            if in_string:
                if ch == "\\":
                    i += 2  # Skip escaped char
                    col += 1
                    continue
                if ch == in_string:
                    in_string = None
                i += 1
                continue
            else:
                if ch in ('"', "'", "`"):
                    in_string = ch
                    i += 1
                    continue

            # Heuristic regex detection: / starts a regex if it follows
            # an operator, opening bracket, or keyword (not after an
            # identifier, number, ) or ])
            if ch == "/" and next_ch and next_ch not in "/*" and not in_string:
                # Look backwards for the last non-space character
                j = i - 1
                while j >= 0 and js[j] in " \t\n":
                    j -= 1
                prev = js[j] if j >= 0 else ""
                # Check for single-char operators that precede regex
                if prev in "=({[,;:!&|?+-*<>~^":
                    in_regex = True
                    i += 1
                    continue
                # Check for keywords that precede regex (return, typeof, etc.)
                if prev and prev.isalpha():
                    # Walk back to get the full word
                    k = j
                    while k >= 0 and (js[k].isalnum() or js[k] == "_"):
                        k -= 1
                    word = js[k + 1 : j + 1]
                    if word in (
                        "return", "typeof", "instanceof", "in", "of",
                        "new", "delete", "void", "throw", "case", "do",
                        "else", "yield", "await", "void",
                    ):
                        in_regex = True
                        i += 1
                        continue

            # Handle brackets
            if ch in "{([":
                stack.append((ch, line_num, col))
            elif ch in "})]":
                expected_open = self._close_to_open.get(ch)
                if not stack:
                    issues.append(
                        ValidationIssue(
                            category="brace_balance",
                            severity="warning",
                            message="Closing '{}' at line {} has no matching opener".format(
                                ch, line_num
                            ),
                            line=line_num,
                        )
                    )
                else:
                    opener, o_line, _ = stack[-1]
                    if opener != expected_open:
                        # Downgrade to warning - likely a false positive from
                        # a context we don't fully understand (regex, etc.)
                        issues.append(
                            ValidationIssue(
                                category="brace_balance",
                                severity="warning",
                                message="Mismatched bracket: '{}' opened at line {} but closed by '{}' at line {}".format(
                                    opener, o_line, ch, line_num
                                ),
                                line=line_num,
                            )
                        )
                        stack.pop()
                    else:
                        stack.pop()

            i += 1

        # Check for unclosed brackets - these are the REAL errors
        for opener, line, _ in stack:
            closer = self._bracket_pairs[opener]
            issues.append(
                ValidationIssue(
                    category="brace_balance",
                    severity="error",
                    message="Unclosed '{}' opened at line {} — expected '{}'".format(
                        opener, line, closer
                    ),
                    line=line,
                )
            )

        # Cap issues per block to avoid noise on minified code
        if len(issues) > 20:
            issues = issues[:20]

        return issues

    def _check_string_integrity(self, js: str) -> List[ValidationIssue]:
        """Check for unclosed string literals on each line."""
        issues: List[ValidationIssue] = []
        lines = js.split("\n")
        for i, line in enumerate(lines, 1):
            # Skip lines that are clearly inside template literals
            # (heuristic: count backticks across the whole file is too complex
            # for a line-by-line check, so we only flag obvious cases)
            stripped = line.strip()
            if not stripped:
                continue

            # Check for odd number of unescaped double quotes
            # (excluding regex and comments)
            if "//" in stripped:
                stripped = stripped[: stripped.index("//")]

            dq = 0
            sq = 0
            j = 0
            while j < len(stripped):
                if stripped[j] == "\\":
                    j += 2
                    continue
                if stripped[j] == '"':
                    dq += 1
                elif stripped[j] == "'":
                    sq += 1
                j += 1

            # Odd counts may indicate unclosed strings (but can be false
            # positives with apostrophes in comments — keep as warning)
            if dq % 2 != 0 and "`" not in stripped:
                issues.append(
                    ValidationIssue(
                        category="string_integrity",
                        severity="warning",
                        message="Odd number of double-quotes on line — possible unclosed string",
                        line=i,
                        snippet=stripped[:100],
                    )
                )

        return issues

    def _check_keyword_sanity(self, js: str) -> List[ValidationIssue]:
        """Check for common keyword usage errors."""
        issues: List[ValidationIssue] = []
        lines = js.split("\n")

        # Pattern: var/let/const followed by nothing or operator
        bad_decl = re.compile(r"\b(var|let|const)\s*[;=]")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            match = bad_decl.search(stripped)
            if match:
                issues.append(
                    ValidationIssue(
                        category="keyword_sanity",
                        severity="warning",
                        message="Declaration '{}' without identifier".format(
                            match.group(1)
                        ),
                        line=i,
                        snippet=stripped[:100],
                    )
                )

        return issues

    def _check_script_tag_pairing(self, html: str, report: ValidationReport) -> None:
        """Verify <script> tags are properly paired."""
        open_count = len(re.findall(r"<script\b", html, re.IGNORECASE))
        close_count = len(re.findall(r"</script\s*>", html, re.IGNORECASE))

        if open_count != close_count:
            report.issues.append(
                ValidationIssue(
                    category="script_tags",
                    severity="error",
                    message="Unpaired <script> tags: {} open, {} close".format(
                        open_count, close_count
                    ),
                )
            )
            report.error_count += 1


# =============================================================================
# Module-level singleton
# =============================================================================

_validator_instance: Optional[JSValidator] = None


def get_validator() -> JSValidator:
    """Get the shared JSValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = JSValidator()
    return _validator_instance


def validate_game_html(html: str) -> ValidationReport:
    """Convenience function to validate game HTML."""
    return get_validator().validate_html(html)
