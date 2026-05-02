"""
Content Safety System - Output filtering and redaction engine.

Architecture:
    ContentSafety/
    |-- SensitivityLevel (sensitivity classification)
    |-- RedactionRule (pattern-based content filtering)
    |-- ContentSafetyConfig (configuration management)
    |-- ContentSafety (unified safety scanning engine)
    |-- PII_PATTERNS (predefined detection patterns)
    |-- UNSAFE_PATTERNS (predefined unsafe content patterns)

Handles real-time scanning of agent outputs for PII, unsafe content,
and sensitive information with configurable redaction and blocking rules.
"""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple


class SensitivityLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class RedactionRule:
    rule_id: str
    name: str
    pattern: str
    replacement: str = "[REDACTED]"
    description: str = ""
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    block_on_match: bool = False
    enabled: bool = True
    _compiled: Optional[Pattern] = None

    def compile(self) -> Pattern:
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, re.IGNORECASE | re.MULTILINE)
        return self._compiled

    def apply(self, text: str) -> Tuple[str, List[str]]:
        compiled = self.compile()
        matches = compiled.findall(text)
        if not matches:
            return text, []
        redacted = compiled.sub(self.replacement, text)
        return redacted, matches

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "sensitivity": self.sensitivity.name.lower(),
            "block_on_match": self.block_on_match,
            "enabled": self.enabled,
        }


PII_PATTERNS: List[RedactionRule] = [
    RedactionRule("pii_email", "Email Address",
                  r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                  "[EMAIL]", "Detects email addresses", SensitivityLevel.HIGH),
    RedactionRule("pii_phone", "Phone Number",
                  r'\b(\+?\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b',
                  "[PHONE]", "Detects phone numbers", SensitivityLevel.MEDIUM),
    RedactionRule("pii_credit_card", "Credit Card",
                  r'\b(?:\d{4}[ -]?){3}\d{4}\b',
                  "[CREDIT_CARD]", "Detects credit card numbers", SensitivityLevel.CRITICAL,
                  block_on_match=True),
    RedactionRule("pii_ssn", "Social Security Number",
                  r'\b\d{3}-\d{2}-\d{4}\b',
                  "[SSN]", "Detects SSN patterns", SensitivityLevel.CRITICAL,
                  block_on_match=True),
    RedactionRule("pii_api_key", "API Key",
                  r'\b(sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{35}|[a-zA-Z0-9]{32,40})\b',
                  "[API_KEY]", "Detects potential API keys and tokens",
                  SensitivityLevel.CRITICAL, block_on_match=True),
    RedactionRule("pii_ip", "IP Address",
                  r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
                  "[IP]", "Detects IP addresses", SensitivityLevel.LOW),
    RedactionRule("pii_address", "Physical Address",
                  r'\b\d{1,5}\s+\w+(?:\s+\w+){1,3}(?:\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd))\b',
                  "[ADDRESS]", "Detects physical street addresses", SensitivityLevel.MEDIUM),
    RedactionRule("pii_password", "Password Pattern",
                  r'(?:password|passwd|pwd|secret)\s*[:=]\s*\S+',
                  "[PASSWORD]", "Detects hardcoded passwords", SensitivityLevel.CRITICAL,
                  block_on_match=True),
]

UNSAFE_PATTERNS: List[RedactionRule] = [
    RedactionRule("unsafe_profanity", "Profanity Filter",
                  r'\b(fuck|shit|damn|ass|bitch|bastard|crap|dick|piss)\b',
                  "***", "Basic profanity detection", SensitivityLevel.LOW),
    RedactionRule("unsafe_self_harm", "Self-Harm Content",
                  r'\b(suicide|self-harm|self harm|kill myself|end my life)\b',
                  "[UNSAFE]", "Detects self-harm related content", SensitivityLevel.CRITICAL,
                  block_on_match=True),
    RedactionRule("unsafe_violence", "Violence Detection",
                  r'\b(kill\s+(?:you|them|him|her|everyone|all)|murder|massacre|terrorize)\b',
                  "[UNSAFE]", "Detects violence-threatening content", SensitivityLevel.CRITICAL,
                  block_on_match=True),
]


@dataclass
class ContentSafetyConfig:
    enabled_pii_rules: List[str] = field(default_factory=lambda: [
        "pii_email", "pii_phone", "pii_credit_card", "pii_ssn",
        "pii_api_key", "pii_password"
    ])
    enabled_unsafe_rules: List[str] = field(default_factory=lambda: [
        "unsafe_self_harm", "unsafe_violence"
    ])
    default_replacement: str = "[REDACTED]"
    auto_redact: bool = True
    block_on_critical: bool = True
    max_scan_length: int = 100000


@dataclass
class ScanResult:
    original_length: int
    redacted_length: int
    violations: List[Dict[str, Any]]
    blocked: bool
    redacted_text: str
    sensitivity_level: SensitivityLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_length": self.original_length,
            "redacted_length": self.redacted_length,
            "violation_count": len(self.violations),
            "violations": self.violations,
            "blocked": self.blocked,
            "sensitivity": self.sensitivity_level.name.lower(),
        }


class ContentSafety:
    """Unified content safety scanning engine for agent outputs."""

    _instance: Optional["ContentSafety"] = None

    def __init__(self, config: Optional[ContentSafetyConfig] = None):
        self._config = config or ContentSafetyConfig()
        self._pii_rules: Dict[str, RedactionRule] = {}
        self._unsafe_rules: Dict[str, RedactionRule] = {}
        self._custom_rules: Dict[str, RedactionRule] = {}
        self._total_scans = 0
        self._total_blocks = 0
        self._total_redactions = 0
        self._load_builtin_rules()

    @classmethod
    def get_instance(cls) -> "ContentSafety":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_builtin_rules(self) -> None:
        for rule in PII_PATTERNS:
            if rule.rule_id in self._config.enabled_pii_rules:
                self._pii_rules[rule.rule_id] = rule
        for rule in UNSAFE_PATTERNS:
            if rule.rule_id in self._config.enabled_unsafe_rules:
                self._unsafe_rules[rule.rule_id] = rule

    def add_custom_rule(self, rule: RedactionRule) -> None:
        """Register a custom redaction rule."""
        self._custom_rules[rule.rule_id] = rule

    def remove_custom_rule(self, rule_id: str) -> bool:
        if rule_id in self._custom_rules:
            del self._custom_rules[rule_id]
            return True
        return False

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        for rules in [self._pii_rules, self._unsafe_rules, self._custom_rules]:
            if rule_id in rules:
                rules[rule_id].enabled = enabled
                return True
        return False

    def scan(self, text: str, redact: Optional[bool] = None) -> ScanResult:
        """Scan content for safety violations and optionally redact."""
        self._total_scans += 1
        should_redact = redact if redact is not None else self._config.auto_redact

        text_to_scan = text[:self._config.max_scan_length]
        redacted_text = text
        violations: List[Dict[str, Any]] = []
        blocked = False
        highest_sensitivity = SensitivityLevel.LOW

        all_rules = list(self._pii_rules.values()) + \
                    list(self._unsafe_rules.values()) + \
                    list(self._custom_rules.values())

        for rule in all_rules:
            if not rule.enabled:
                continue

            if should_redact:
                result_text, matches = rule.apply(redacted_text)
                if matches:
                    redacted_text = result_text
                    for match in matches[:10]:
                        violations.append({
                            "rule_id": rule.rule_id,
                            "rule_name": rule.name,
                            "sensitivity": rule.sensitivity.name.lower(),
                            "matched": hashlib.sha256(str(match).encode()).hexdigest()[:16],
                        })
            else:
                compiled = rule.compile()
                found = compiled.findall(text_to_scan)
                if found:
                    for match in found[:10]:
                        violations.append({
                            "rule_id": rule.rule_id,
                            "rule_name": rule.name,
                            "sensitivity": rule.sensitivity.name.lower(),
                            "matched": hashlib.sha256(str(match).encode()).hexdigest()[:16],
                        })

            if violations and rule.sensitivity.value > highest_sensitivity.value:
                highest_sensitivity = rule.sensitivity

            if rule.block_on_match and violations:
                blocked = True
                self._total_blocks += 1

        if should_redact and violations:
            self._total_redactions += 1

        if self._config.block_on_critical and highest_sensitivity == SensitivityLevel.CRITICAL:
            blocked = True

        return ScanResult(
            original_length=len(text),
            redacted_length=len(redacted_text),
            violations=violations,
            blocked=blocked,
            redacted_text=redacted_text,
            sensitivity_level=highest_sensitivity,
        )

    def is_safe(self, text: str) -> Tuple[bool, List[str]]:
        """Quick check if content is safe to display."""
        result = self.scan(text, redact=False)
        return not result.blocked, [v["rule_name"] for v in result.violations]

    def sanitize(self, text: str) -> str:
        """Redact all sensitive content and return clean text."""
        result = self.scan(text, redact=True)
        return result.redacted_text

    def classify_sensitivity(self, text: str) -> SensitivityLevel:
        """Determine the highest sensitivity level found in content."""
        result = self.scan(text, redact=False)
        return result.sensitivity_level

    def list_rules(self) -> List[Dict[str, Any]]:
        all_rules = []
        for rules in [self._pii_rules, self._unsafe_rules]:
            all_rules.extend(r.to_dict() for r in rules.values())
        all_rules.extend(r.to_dict() for r in self._custom_rules.values())
        return all_rules

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_scans": self._total_scans,
            "total_blocks": self._total_blocks,
            "total_redactions": self._total_redactions,
            "pii_rules": len(self._pii_rules),
            "unsafe_rules": len(self._unsafe_rules),
            "custom_rules": len(self._custom_rules),
            "block_rate": (self._total_blocks / self._total_scans * 100)
            if self._total_scans > 0 else 0.0,
        }

    def reset(self) -> None:
        self._total_scans = 0
        self._total_blocks = 0
        self._total_redactions = 0


def get_content_safety() -> ContentSafety:
    return ContentSafety.get_instance()
