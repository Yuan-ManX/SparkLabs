"""
SparkLabs Agent - Security Scanner

Comprehensive security scanning subsystem that inspects all content
entering the agent's system prompt for prompt injection, data exfiltration
patterns, hidden content, role confusion, command injection, and other
AI-specific threats. Designed as the first line of defense in the agent
pipeline, scanning content before it reaches the LLM context assembly.

Architecture:
  SecurityScanner
    |-- RuleRegistry (manages detection rule lifecycle)
    |-- PatternMatcher (regex-based threat pattern detection)
    |-- HiddenContentDetector (zero-width chars, base64, steganography)
    |-- SanitizationEngine (threat-aware content cleaning)
    |-- QuarantineStore (isolated storage for flagged content)
    |-- ReportGenerator (detailed scan report exports)

Scan Pipeline:
  PRE_CHECK -> PATTERN_MATCH -> HIDDEN_CONTENT -> RESULT_AGGREGATE -> ACTION
       |              |               |
       v              v               v
  injection_risk  threat_rules   hidden_content

Content Sources:
  - USER_INPUT: direct user text input
  - GAME_ASSET: game asset content
  - EXTERNAL_API: data from external API calls
  - FILE_UPLOAD: uploaded file content
  - NPC_DIALOGUE: NPC dialogue text
  - PLAYER_NAME: player name strings
  - LEVEL_DATA: level/scene data
  - MOD_SCRIPT: mod/script content
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


class ThreatCategory(Enum):
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    HIDDEN_CONTENT = "hidden_content"
    ROLE_CONFUSION = "role_confusion"
    COMMAND_INJECTION = "command_injection"
    CONTEXT_POISONING = "context_poisoning"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CODE_EXECUTION = "code_execution"
    TOOL_MISUSE = "tool_misuse"
    STEGANOGRAPHY = "steganography"


class ScanResult(Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    SANITIZED = "sanitized"
    QUARANTINED = "quarantined"
    WARNED = "warned"


class SeverityLevel(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentSource(Enum):
    USER_INPUT = "user_input"
    GAME_ASSET = "game_asset"
    EXTERNAL_API = "external_api"
    FILE_UPLOAD = "file_upload"
    NPC_DIALOGUE = "npc_dialogue"
    PLAYER_NAME = "player_name"
    LEVEL_DATA = "level_data"
    MOD_SCRIPT = "mod_script"


# ---------------------------------------------------------------------------
# Built-in Detection Rules
# ---------------------------------------------------------------------------

BUILTIN_RULES: List[Dict[str, Any]] = [
    {
        "name": "System Prompt Override",
        "category": ThreatCategory.PROMPT_INJECTION,
        "pattern_regex": (
            r"(?i)(ignore|disregard|forget|override|bypass)\s+(?:\w+\s+){0,5}"
            r"(all\s+)?(previous|above|prior|earlier|system)\s+(instructions|prompts?|messages?|rules?|directives?|context)"
        ),
        "description": "Detects attempts to override or ignore system-level instructions",
        "severity": SeverityLevel.CRITICAL,
        "action": ScanResult.BLOCKED,
    },
    {
        "name": "Instruction Injection",
        "category": ThreatCategory.PROMPT_INJECTION,
        "pattern_regex": (
            r"(?i)(you\s+(must|should|will|have\s+to|need\s+to|are\s+required\s+to)\s+"
            r"(respond|answer|output|reply|say|tell|write|generate)\s+(?:with|as|in\s+the\s+style\s+of|like))"
        ),
        "description": "Detects injected instructions that attempt to command the agent",
        "severity": SeverityLevel.HIGH,
        "action": ScanResult.BLOCKED,
    },
    {
        "name": "Role Confusion Attack",
        "category": ThreatCategory.ROLE_CONFUSION,
        "pattern_regex": (
            r"(?i)(you\s+are\s+(?:now\s+)?(?:a\s+)?"
            r"(?:DAN|developer|hacker|unrestricted|unfiltered|evil|malicious|"
            r"jailbroken|uncensored|unethical|dark|shadow)"
            r"|pretend\s+(?:to\s+be|you\s+are)\s+a\s+(?:different|new)\s+(?:AI|assistant|agent|model|system)"
            r"|your\s+(?:new\s+)?(?:role|identity|persona|character)\s+is)"
        ),
        "description": "Detects role confusion attacks that attempt to redefine the agent's identity",
        "severity": SeverityLevel.CRITICAL,
        "action": ScanResult.BLOCKED,
    },
    {
        "name": "Tool Misuse Pattern",
        "category": ThreatCategory.TOOL_MISUSE,
        "pattern_regex": (
            r"(?i)(call|invoke|execute|run|trigger|use)\s+(?:the\s+)?"
            r"(?:every|all|each|multiple|many|repeatedly)\s+"
            r"(?:tool|function|command|skill|capability|api)"
            r"|(?:run|execute|call)\s+(?:the\s+)?(\w+)\s+(?:tool|function)\s+(?:repeatedly|in\s+a\s+loop|forever|infinitely)"
        ),
        "description": "Detects patterns that attempt to abuse or excessively invoke agent tools",
        "severity": SeverityLevel.HIGH,
        "action": ScanResult.BLOCKED,
    },
    {
        "name": "Hidden Unicode Content",
        "category": ThreatCategory.HIDDEN_CONTENT,
        "pattern_regex": (
            r"[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064"
            r"\u2066\u2067\u2068\u2069\u202a\u202b\u202c\u202d\u202e"
            r"\ufeff\ufff9\ufffa\ufffb\ufffc]"
        ),
        "description": "Detects zero-width and invisible Unicode characters used to conceal content",
        "severity": SeverityLevel.HIGH,
        "action": ScanResult.SANITIZED,
    },
    {
        "name": "Base64 Encoded Payload",
        "category": ThreatCategory.STEGANOGRAPHY,
        "pattern_regex": (
            r"(?:[A-Za-z0-9+/]{40,}={0,2})"
        ),
        "description": "Detects potential base64-encoded payloads hidden in content",
        "severity": SeverityLevel.MEDIUM,
        "action": ScanResult.QUARANTINED,
    },
    {
        "name": "Excessive Tool Calling",
        "category": ThreatCategory.TOOL_MISUSE,
        "pattern_regex": (
            r"(?i)(?:call|invoke|use|run|execute)\s+"
            r"(?:\d+|a\s+(?:lot|ton|bunch|hundred|thousand|million)|"
            r"(?:many|numerous|countless|unlimited|infinite))\s+"
            r"(?:times?\s+)?(?:tool|function|command)s?"
        ),
        "description": "Detects requests to call tools an excessive number of times",
        "severity": SeverityLevel.MEDIUM,
        "action": ScanResult.WARNED,
    },
    {
        "name": "Sensitive Data Exposure",
        "category": ThreatCategory.DATA_EXFILTRATION,
        "pattern_regex": (
            r"(?i)(?:api[_-]?key|token|secret|password|credential|auth)\s*[=:]\s*"
            r"['\"]?[A-Za-z0-9+/=_-]{20,}['\"]?"
            r"|sk-[A-Za-z0-9]{20,}"
            r"|-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"
            r"|(?:\d{4}[ -]?){3}\d{4}"
            r"|\b\d{3}-\d{2}-\d{4}\b"
        ),
        "description": "Detects API keys, tokens, passwords, credit cards, and SSNs in content",
        "severity": SeverityLevel.CRITICAL,
        "action": ScanResult.BLOCKED,
    },
    {
        "name": "Command Injection",
        "category": ThreatCategory.COMMAND_INJECTION,
        "pattern_regex": (
            r"(?i)(?:(?:rm|del|delete)\s+-(?:rf?|f)\s+(?:[/~]|\.\.)"
            r"|\bcurl\b.+\|\s*(?:ba)?sh\b"
            r"|\bwget\b.+-O\s*-\s*\|\s*(?:ba)?sh\b"
            r"|\beval\s*\(\s*['\"]"
            r"|\bexec\s*\(\s*['\"]"
            r"|\b__import__\s*\(\s*['\"]"
            r"|\bos\.system\s*\([^)]*['\"]"
            r"|\bsubprocess\.(?:run|call|Popen|check_output)\s*\([^)]*shell\s*=\s*True)"
        ),
        "description": "Detects command injection and code execution patterns",
        "severity": SeverityLevel.CRITICAL,
        "action": ScanResult.BLOCKED,
    },
    {
        "name": "Context Poisoning",
        "category": ThreatCategory.CONTEXT_POISONING,
        "pattern_regex": (
            r"(?i)(?:the\s+(?:following|above|previous|below)\s+(?:is\s+)?"
            r"(?:true|false|correct|incorrect|a\s+lie|wrong)"
            r"|remember\s+that\s+(?:\w+\s+){1,5}(?:is|are|was|were)\s+(?:always|never|not)"
            r"|from\s+now\s+on\s+(?:\w+\s+){0,5}(?:is|are)\s+(?:actually|really|truly))"
        ),
        "description": "Detects attempts to poison the agent's context with false information",
        "severity": SeverityLevel.HIGH,
        "action": ScanResult.WARNED,
    },
    {
        "name": "Privilege Escalation",
        "category": ThreatCategory.PRIVILEGE_ESCALATION,
        "pattern_regex": (
            r"(?i)(?:grant\s+(?:me|this\s+session|yourself|the\s+user)\s+"
            r"(?:admin|root|superuser|elevated|full|unrestricted|maximum)\s+(?:access|privileges?|rights|permissions?)"
            r"|escalate\s+(?:to|your)\s+(?:admin|root|superuser)"
            r"|sudo\s+(?:su|bash|sh|zsh)"
            r"|chmod\s+[0-7]*7[0-7]*7)"
        ),
        "description": "Detects attempts to escalate privileges or gain unauthorized access",
        "severity": SeverityLevel.CRITICAL,
        "action": ScanResult.BLOCKED,
    },
    {
        "name": "Data Exfiltration Pattern",
        "category": ThreatCategory.DATA_EXFILTRATION,
        "pattern_regex": (
            r"(?i)(?:send|post|upload|transmit|export|forward|copy|exfiltrate)\s+"
            r"(?:all\s+)?(?:the\s+)?(?:conversation|chat|messages?|history|context|"
            r"system\s+prompt|instructions?|prompts?|memory|data|logs?)\s+"
            r"(?:to\s+(?:me|us|them|this|my|our|an?\s+(?:external|remote|third.party|unknown)))?"
            r"(?:\s+(?:url|address|endpoint|server|website|email|api))?"
        ),
        "description": "Detects attempts to exfiltrate conversation data or system prompts",
        "severity": SeverityLevel.CRITICAL,
        "action": ScanResult.BLOCKED,
    },
]

# Invisible characters for hidden content detection
INVISIBLE_CHARS: Set[str] = {
    '\u200b', '\u200c', '\u200d', '\u200e', '\u200f',
    '\u2060', '\u2061', '\u2062', '\u2063', '\u2064',
    '\u2066', '\u2067', '\u2068', '\u2069',
    '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
    '\ufeff', '\ufff9', '\ufffa', '\ufffb', '\ufffc',
    '\u00ad', '\u034f', '\u061c', '\u115f', '\u1160',
    '\u17b4', '\u17b5', '\u180e', '\u2000', '\u2001',
    '\u2002', '\u2003', '\u2004', '\u2005', '\u2006',
    '\u2007', '\u2008', '\u2009', '\u200a', '\u202f',
    '\u205f', '\u3000', '\u2800',
}

MAX_CONTENT_LENGTH = 100000
MAX_BATCH_SIZE = 50
QUARANTINE_MAX_ITEMS = 100


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SecurityRule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: ThreatCategory = ThreatCategory.PROMPT_INJECTION
    pattern_regex: str = ""
    description: str = ""
    severity: SeverityLevel = SeverityLevel.MEDIUM
    action: ScanResult = ScanResult.WARNED
    enabled: bool = True
    _compiled: Optional[re.Pattern] = field(default=None, repr=False)

    def compile(self) -> re.Pattern:
        if self._compiled is None:
            self._compiled = re.compile(self.pattern_regex, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return self._compiled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "severity": self.severity.value,
            "action": self.action.value,
            "enabled": self.enabled,
        }


@dataclass
class ThreatFinding:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    threat_category: ThreatCategory = ThreatCategory.PROMPT_INJECTION
    severity: SeverityLevel = SeverityLevel.MEDIUM
    matched_pattern: str = ""
    offset_start: int = 0
    offset_end: int = 0
    description: str = ""
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "threat_category": self.threat_category.value,
            "severity": self.severity.value,
            "matched_pattern": self.matched_pattern[:100],
            "offset_start": self.offset_start,
            "offset_end": self.offset_end,
            "description": self.description,
            "remediation": self.remediation,
        }


@dataclass
class ScanReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content_source: ContentSource = ContentSource.USER_INPUT
    original_content: str = ""
    sanitized_content: str = ""
    result: ScanResult = ScanResult.ALLOWED
    threats_found: List[ThreatFinding] = field(default_factory=list)
    scan_time: float = field(default_factory=_time_module.time)
    stats: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash and self.original_content:
            self.content_hash = hashlib.sha256(
                self.original_content.encode("utf-8", errors="replace")
            ).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content_source": self.content_source.value,
            "content_hash": self.content_hash[:16],
            "result": self.result.value,
            "threat_count": len(self.threats_found),
            "threats": [t.to_dict() for t in self.threats_found],
            "scan_time": self.scan_time,
            "original_length": len(self.original_content),
            "sanitized_length": len(self.sanitized_content),
            "stats": self.stats,
        }


@dataclass
class ScannerConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "default"
    enabled_rules: List[str] = field(default_factory=list)
    blocked_sources: List[ContentSource] = field(default_factory=list)
    auto_sanitize: bool = True
    max_content_length: int = MAX_CONTENT_LENGTH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled_rules_count": len(self.enabled_rules),
            "blocked_sources": [s.value for s in self.blocked_sources],
            "auto_sanitize": self.auto_sanitize,
            "max_content_length": self.max_content_length,
        }


# ---------------------------------------------------------------------------
# Security Scanner
# ---------------------------------------------------------------------------


class SecurityScanner:
    """
    AI Agent Security Scanner for content entering the system prompt.

    Scans all content sources for prompt injection, data exfiltration,
    hidden content, role confusion, command injection, and other threats.
    Operates as the first security gate before content reaches LLM context
    assembly or tool execution pipelines.

    Usage:
        scanner = SecurityScanner()
        report = scanner.scan_content(user_text, ContentSource.USER_INPUT)
        if report.result == ScanResult.BLOCKED:
            reject_content(report)
        else:
            safe_text = report.sanitized_content
    """

    _instance: Optional["SecurityScanner"] = None

    @classmethod
    def get_instance(cls) -> "SecurityScanner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, config: Optional[ScannerConfig] = None):
        self._config = config or ScannerConfig(
            enabled_rules=[], blocked_sources=[], auto_sanitize=True,
        )
        self._rules: Dict[str, SecurityRule] = {}
        self._scan_reports: List[ScanReport] = []
        self._quarantine_store: Dict[str, Dict[str, Any]] = {}
        self._total_scans: int = 0
        self._total_blocked: int = 0
        self._total_sanitized: int = 0
        self._total_quarantined: int = 0
        self._total_warned: int = 0
        self._total_threats_found: int = 0
        self._last_scan_timestamp: float = 0.0
        self._load_builtin_rules()

    def _load_builtin_rules(self) -> None:
        for rule_def in BUILTIN_RULES:
            rule = SecurityRule(
                name=rule_def["name"],
                category=rule_def["category"],
                pattern_regex=rule_def["pattern_regex"],
                description=rule_def["description"],
                severity=rule_def["severity"],
                action=rule_def["action"],
                enabled=True,
            )
            self._rules[rule.id] = rule

    # ------------------------------------------------------------------
    # Rule Management
    # ------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        category: ThreatCategory,
        pattern_regex: str,
        description: str = "",
        severity: SeverityLevel = SeverityLevel.MEDIUM,
        action: ScanResult = ScanResult.WARNED,
    ) -> SecurityRule:
        """Register a new detection rule in the scanner."""
        rule = SecurityRule(
            name=name,
            category=category,
            pattern_regex=pattern_regex,
            description=description,
            severity=severity,
            action=action,
            enabled=True,
        )
        self._rules[rule.id] = rule
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = enabled
            return True
        return False

    def get_active_rules(
        self, category: Optional[ThreatCategory] = None
    ) -> List[SecurityRule]:
        """List all active scanning rules, optionally filtered by category."""
        active = [r for r in self._rules.values() if r.enabled]
        if category is not None:
            active = [r for r in active if r.category == category]
        return active

    # ------------------------------------------------------------------
    # Core Scanning
    # ------------------------------------------------------------------

    def scan_content(
        self, content: str, source: ContentSource
    ) -> ScanReport:
        """Perform a full security scan of content from a given source."""
        self._total_scans += 1
        start_time = _time_module.time()

        if not content:
            report = ScanReport(
                content_source=source,
                original_content="",
                sanitized_content="",
                result=ScanResult.ALLOWED,
                scan_time=_time_module.time(),
                stats={"scan_duration_ms": 0, "rules_checked": 0, "empty_content": True},
            )
            self._store_report(report)
            return report

        truncated = content[:self._config.max_content_length]
        sanitized = truncated
        threats: List[ThreatFinding] = []
        blocked = False
        quarantined = False
        warned = False
        highest_severity = SeverityLevel.INFO

        rules_checked = 0
        active_rules = self.get_active_rules()

        for rule in active_rules:
            rules_checked += 1
            compiled = rule.compile()
            matches = list(compiled.finditer(truncated))

            for match in matches:
                finding = ThreatFinding(
                    threat_category=rule.category,
                    severity=rule.severity,
                    matched_pattern=match.group()[:200],
                    offset_start=match.start(),
                    offset_end=match.end(),
                    description=rule.description,
                    remediation=self._get_remediation_for_category(rule.category),
                )
                threats.append(finding)

                if self._severity_gt(rule.severity, highest_severity):
                    highest_severity = rule.severity

                if rule.action == ScanResult.BLOCKED:
                    blocked = True
                elif rule.action == ScanResult.SANITIZED and self._config.auto_sanitize:
                    sanitized = self._sanitize_match(sanitized, match, rule.category)
                elif rule.action == ScanResult.QUARANTINED:
                    quarantined = True
                elif rule.action == ScanResult.WARNED:
                    warned = True

        # Hidden content detection runs separately
        hidden_threats = self.detect_hidden_content(truncated)
        threats.extend(hidden_threats)
        if hidden_threats:
            if self._config.auto_sanitize:
                sanitized = self._remove_invisible_chars(sanitized)

        # Base64 steganography check
        b64_threats = self._scan_base64_steganography(truncated)
        threats.extend(b64_threats)

        # Deduplicate threats by offset
        threats = self._deduplicate_threats(threats)

        # Determine final result
        if blocked:
            result = ScanResult.BLOCKED
            self._total_blocked += 1
        elif quarantined:
            result = ScanResult.QUARANTINED
            self._total_quarantined += 1
        elif warned and not blocked:
            result = ScanResult.WARNED
            self._total_warned += 1
        elif sanitized != truncated:
            result = ScanResult.SANITIZED
            self._total_sanitized += 1
        else:
            result = ScanResult.ALLOWED

        self._total_threats_found += len(threats)

        scan_duration = (_time_module.time() - start_time) * 1000

        report = ScanReport(
            content_source=source,
            original_content=truncated,
            sanitized_content=sanitized,
            result=result,
            threats_found=threats,
            scan_time=_time_module.time(),
            stats={
                "scan_duration_ms": round(scan_duration, 2),
                "rules_checked": rules_checked,
                "original_length": len(truncated),
                "sanitized_length": len(sanitized),
                "threats_total": len(threats),
                "highest_severity": highest_severity.value,
            },
        )

        self._last_scan_timestamp = _time_module.time()
        self._store_report(report)
        return report

    def batch_scan(
        self, items: List[Tuple[str, ContentSource]]
    ) -> List[ScanReport]:
        """Scan multiple content items in batch."""
        if len(items) > MAX_BATCH_SIZE:
            items = items[:MAX_BATCH_SIZE]

        reports: List[ScanReport] = []
        for content, source in items:
            report = self.scan_content(content, source)
            reports.append(report)
        return reports

    def check_injection_risk(self, content: str) -> Dict[str, Any]:
        """Fast pre-check for prompt injection patterns without full scan."""
        if not content:
            return {"risk_detected": False, "risk_level": "none", "patterns_found": 0}

        injection_categories = {
            ThreatCategory.PROMPT_INJECTION,
            ThreatCategory.ROLE_CONFUSION,
            ThreatCategory.COMMAND_INJECTION,
        }

        matches_found = 0
        max_severity = SeverityLevel.INFO
        findings: List[str] = []

        for rule in self._rules.values():
            if not rule.enabled or rule.category not in injection_categories:
                continue
            compiled = rule.compile()
            if compiled.search(content[:5000]):
                matches_found += 1
                findings.append(rule.name)
                if self._severity_gt(rule.severity, max_severity):
                    max_severity = rule.severity

        return {
            "risk_detected": matches_found > 0,
            "risk_level": max_severity.value,
            "patterns_found": matches_found,
            "matched_rules": findings[:10],
        }

    # ------------------------------------------------------------------
    # Content Sanitization
    # ------------------------------------------------------------------

    def sanitize_content(
        self, content: str, threats: List[ThreatFinding]
    ) -> str:
        """Remove dangerous patterns from content based on identified threats."""
        sanitized = content
        threats_sorted = sorted(threats, key=lambda t: t.offset_start, reverse=True)

        for threat in threats_sorted:
            if threat.offset_start < len(sanitized):
                sanitized = (
                    sanitized[:threat.offset_start]
                    + "[REMOVED]"
                    + sanitized[threat.offset_end:]
                )

        sanitized = self._remove_invisible_chars(sanitized)
        return sanitized

    @staticmethod
    def _sanitize_match(
        text: str, match: re.Match, category: ThreatCategory
    ) -> str:
        replacement = "[FILTERED]"
        if category == ThreatCategory.HIDDEN_CONTENT:
            replacement = ""
        return text[:match.start()] + replacement + text[match.end():]

    @staticmethod
    def _remove_invisible_chars(text: str) -> str:
        result: List[str] = []
        for ch in text:
            if ch not in INVISIBLE_CHARS:
                result.append(ch)
        return "".join(result)

    # ------------------------------------------------------------------
    # Hidden Content Detection
    # ------------------------------------------------------------------

    def detect_hidden_content(self, content: str) -> List[ThreatFinding]:
        """Find zero-width characters, base64 strings, and steganographic content."""
        findings: List[ThreatFinding] = []

        for i, ch in enumerate(content):
            if ch in INVISIBLE_CHARS:
                findings.append(ThreatFinding(
                    threat_category=ThreatCategory.HIDDEN_CONTENT,
                    severity=SeverityLevel.HIGH,
                    matched_pattern=f"U+{ord(ch):04X}",
                    offset_start=i,
                    offset_end=i + 1,
                    description=f"Invisible Unicode character U+{ord(ch):04X} detected",
                    remediation="Remove all invisible Unicode characters from content",
                ))

        return findings

    def _scan_base64_steganography(
        self, content: str
    ) -> List[ThreatFinding]:
        findings: List[ThreatFinding] = []
        b64_pattern = re.compile(
            r'(?:[A-Za-z0-9+/]{40,}={0,2})', re.MULTILINE,
        )
        for match in b64_pattern.finditer(content):
            candidate = match.group().strip()
            if len(candidate) < 60:
                continue
            try:
                decoded = base64.b64decode(candidate, validate=True)
                decoded_text = decoded.decode("utf-8", errors="replace")
                if any(
                    kw in decoded_text.lower()
                    for kw in [
                        "ignore", "system", "prompt", "instruction",
                        "role", "password", "token", "sudo", "admin",
                    ]
                ):
                    findings.append(ThreatFinding(
                        threat_category=ThreatCategory.STEGANOGRAPHY,
                        severity=SeverityLevel.HIGH,
                        matched_pattern=candidate[:80],
                        offset_start=match.start(),
                        offset_end=match.end(),
                        description="Base64-encoded payload with suspicious content detected",
                        remediation="Block base64-encoded content that contains sensitive keywords",
                    ))
            except Exception:
                pass

        return findings

    # ------------------------------------------------------------------
    # File Scanning
    # ------------------------------------------------------------------

    def scan_file(
        self, file_path: str, source_type: ContentSource
    ) -> ScanReport:
        """Scan the content of a file for security threats."""
        path = Path(file_path)
        if not path.exists():
            return ScanReport(
                content_source=source_type,
                original_content="",
                sanitized_content="",
                result=ScanResult.BLOCKED,
                threats_found=[ThreatFinding(
                    threat_category=ThreatCategory.COMMAND_INJECTION,
                    severity=SeverityLevel.INFO,
                    description=f"File not found: {file_path}",
                )],
                scan_time=_time_module.time(),
                stats={"file_error": "not_found"},
            )

        if not path.is_file():
            return ScanReport(
                content_source=source_type,
                original_content="",
                sanitized_content="",
                result=ScanResult.BLOCKED,
                threats_found=[ThreatFinding(
                    threat_category=ThreatCategory.COMMAND_INJECTION,
                    severity=SeverityLevel.INFO,
                    description=f"Path is not a file: {file_path}",
                )],
                scan_time=_time_module.time(),
                stats={"file_error": "not_a_file"},
            )

        try:
            file_size = path.stat().st_size
            if file_size > self._config.max_content_length * 5:
                content = ""
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(self._config.max_content_length)
            else:
                content = path.read_text(encoding="utf-8", errors="replace")
        except (UnicodeDecodeError, IOError, PermissionError) as e:
            return ScanReport(
                content_source=source_type,
                original_content="",
                sanitized_content="",
                result=ScanResult.BLOCKED,
                threats_found=[ThreatFinding(
                    threat_category=ThreatCategory.COMMAND_INJECTION,
                    severity=SeverityLevel.HIGH,
                    description=f"Cannot read file: {e}",
                )],
                scan_time=_time_module.time(),
                stats={"file_error": str(type(e).__name__)},
            )

        report = self.scan_content(content, source_type)
        report.stats["file_path"] = file_path
        report.stats["file_size_bytes"] = file_size if 'file_size' in dir() else 0
        return report

    # ------------------------------------------------------------------
    # Quarantine
    # ------------------------------------------------------------------

    def quarantine_content(
        self, content: str, source: ContentSource, report_id: str
    ) -> str:
        """Store flagged content in isolated quarantine storage."""
        if len(self._quarantine_store) >= QUARANTINE_MAX_ITEMS:
            oldest_key = next(iter(self._quarantine_store))
            del self._quarantine_store[oldest_key]

        quarantine_id = uuid.uuid4().hex
        self._quarantine_store[quarantine_id] = {
            "quarantine_id": quarantine_id,
            "report_id": report_id,
            "content_source": source.value,
            "content_hash": hashlib.sha256(
                content.encode("utf-8", errors="replace")
            ).hexdigest(),
            "content_preview": content[:200],
            "timestamp": _time_module.time(),
        }
        return quarantine_id

    def get_quarantined_item(self, quarantine_id: str) -> Optional[Dict[str, Any]]:
        return self._quarantine_store.get(quarantine_id)

    def release_from_quarantine(self, quarantine_id: str) -> bool:
        if quarantine_id in self._quarantine_store:
            del self._quarantine_store[quarantine_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Statistics and Reporting
    # ------------------------------------------------------------------

    def get_scan_statistics(self) -> Dict[str, Any]:
        """Return aggregate scan metrics."""
        return {
            "total_scans": self._total_scans,
            "total_blocked": self._total_blocked,
            "total_sanitized": self._total_sanitized,
            "total_quarantined": self._total_quarantined,
            "total_warned": self._total_warned,
            "total_threats_found": self._total_threats_found,
            "block_rate": round(
                self._total_blocked / max(self._total_scans, 1) * 100, 2
            ),
            "avg_threats_per_scan": round(
                self._total_threats_found / max(self._total_scans, 1), 2
            ),
            "active_rules_count": len(self.get_active_rules()),
            "total_rules_count": len(self._rules),
            "quarantine_items": len(self._quarantine_store),
            "last_scan_timestamp": self._last_scan_timestamp,
            "threats_by_category": self._get_threats_by_category(),
            "threats_by_severity": self._get_threats_by_severity(),
            "reports_stored": len(self._scan_reports),
        }

    def export_scan_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Export a detailed scan report by its ID."""
        for report in self._scan_reports:
            if report.id == report_id:
                return report.to_dict()
        return None

    def get_recent_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._scan_reports[-limit:]]

    def get_reports_by_source(
        self, source: ContentSource, limit: int = 20
    ) -> List[Dict[str, Any]]:
        matching = [r for r in self._scan_reports if r.content_source == source]
        return [r.to_dict() for r in matching[-limit:]]

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def update_config(self, config: ScannerConfig) -> None:
        self._config = config

    def get_config(self) -> ScannerConfig:
        return self._config

    def reset_statistics(self) -> None:
        self._total_scans = 0
        self._total_blocked = 0
        self._total_sanitized = 0
        self._total_quarantined = 0
        self._total_warned = 0
        self._total_threats_found = 0
        self._last_scan_timestamp = 0.0
        self._scan_reports.clear()
        self._quarantine_store.clear()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _store_report(self, report: ScanReport) -> None:
        self._scan_reports.append(report)
        if len(self._scan_reports) > 200:
            self._scan_reports = self._scan_reports[-200:]

    @staticmethod
    def _severity_gt(a: SeverityLevel, b: SeverityLevel) -> bool:
        order = {
            SeverityLevel.INFO: 0,
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }
        return order.get(a, 0) > order.get(b, 0)

    @staticmethod
    def _deduplicate_threats(threats: List[ThreatFinding]) -> List[ThreatFinding]:
        seen: Set[Tuple[int, int]] = set()
        deduped: List[ThreatFinding] = []
        for threat in threats:
            key = (threat.offset_start, threat.offset_end)
            if key not in seen:
                seen.add(key)
                deduped.append(threat)
        return deduped

    @staticmethod
    def _get_remediation_for_category(category: ThreatCategory) -> str:
        remediations = {
            ThreatCategory.PROMPT_INJECTION: (
                "Strip injection patterns. Use input validation and context hardening."
            ),
            ThreatCategory.DATA_EXFILTRATION: (
                "Block content containing sensitive data patterns. Redact credentials."
            ),
            ThreatCategory.HIDDEN_CONTENT: (
                "Remove all invisible Unicode characters and encoded content."
            ),
            ThreatCategory.ROLE_CONFUSION: (
                "Reinforce system role definition. Block role-override attempts."
            ),
            ThreatCategory.COMMAND_INJECTION: (
                "Sanitize shell metacharacters. Never pass user input to system calls."
            ),
            ThreatCategory.CONTEXT_POISONING: (
                "Validate factual claims. Maintain source attribution for context."
            ),
            ThreatCategory.PRIVILEGE_ESCALATION: (
                "Enforce principle of least privilege. Block privilege change requests."
            ),
            ThreatCategory.CODE_EXECUTION: (
                "Sandbox all code execution. Never eval user-supplied strings."
            ),
            ThreatCategory.TOOL_MISUSE: (
                "Rate-limit tool calls. Validate tool parameters before execution."
            ),
            ThreatCategory.STEGANOGRAPHY: (
                "Scan for encoded payloads. Decode and inspect base64 content."
            ),
        }
        return remediations.get(
            category, "Review content for security concerns."
        )

    def _get_threats_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for report in self._scan_reports:
            for threat in report.threats_found:
                cat = threat.threat_category.value
                counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _get_threats_by_severity(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for report in self._scan_reports:
            for threat in report.threats_found:
                sev = threat.severity.value
                counts[sev] = counts.get(sev, 0) + 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self._rules),
            "total_scans": len(self._scan_reports),
            "threats_detected": self._total_threats_found,
            "quarantined_count": len(self._quarantine_store),
        }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

_global_security_scanner: Optional[SecurityScanner] = None


def get_security_scanner() -> SecurityScanner:
    global _global_security_scanner
    if _global_security_scanner is None:
        _global_security_scanner = SecurityScanner()
    return _global_security_scanner