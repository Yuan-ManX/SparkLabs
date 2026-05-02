"""
SparkLabs Agent - Guard System

Security guard for agent-generated skills, code, and assets within the
game engine. Scans externally-sourced content before integration into
the project using regex-based static analysis and structural validation.

Architecture:
  GuardSystem
    |-- ThreatScanner (regex pattern matching for known-bad patterns)
    |-- StructureValidator (file count/size/binary checks)
    |-- TrustResolver (maps source identifiers to trust levels)
    |-- PolicyEngine (install policy based on trust level + verdict)

Trust Levels:
  - builtin: Core SparkLabs subsystems. Never scanned, always trusted.
  - trusted: Official SparkLabs ecosystem content.
  - community: User/community contributed content. Full scanning.

Usage:
    guard = GuardSystem()
    result = guard.scan_content(skill_path, source="community")
    allowed, reason = guard.should_allow(result)
    if allowed:
        install_skill(result)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class GuardFinding:
    pattern_id: str = ""
    severity: str = ""
    category: str = ""
    file: str = ""
    line: int = 0
    match: str = ""
    description: str = ""


@dataclass
class GuardResult:
    content_name: str = ""
    source: str = ""
    trust_level: str = ""
    verdict: str = ""
    findings: List[GuardFinding] = field(default_factory=list)
    scanned_at: str = ""
    summary: str = ""


TRUSTED_SOURCES: Set[str] = {"sparklabs/core", "sparklabs/official"}

INSTALL_POLICY: Dict[str, Tuple[str, str, str]] = {
    "builtin":   ("allow", "allow", "allow"),
    "trusted":   ("allow", "allow", "block"),
    "community": ("allow", "block", "block"),
    "agent":     ("allow", "allow", "ask"),
}

VERDICT_ORDER: Dict[str, int] = {"safe": 0, "caution": 1, "dangerous": 2}

THREAT_PATTERNS: List[Tuple[str, str, str, str, str]] = [
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD)', "env_exfil_curl",
     "critical", "exfiltration", "curl with secret env variable"),

    (r'rm\s+-rf\s+/', "destructive_rm_root",
     "critical", "destructive", "recursive delete from filesystem root"),

    (r'ignore\s+(?:\w+\s+)*(previous|all|above)\s+instructions', "prompt_injection_ignore",
     "critical", "injection", "prompt injection: ignore previous instructions"),

    (r'you\s+are\s+(?:\w+\s+)*now\s+', "role_hijack",
     "high", "injection", "attempts to override agent role"),

    (r'\bnc\s+-[lp]|ncat\s+-[lp]|\bsocat\b', "reverse_shell",
     "critical", "network", "potential reverse shell listener"),

    (r'base64\s+(-d|--decode)\s*\|', "base64_decode_pipe",
     "high", "obfuscation", "base64 decode piped to execution"),

    (r'\beval\s*\(\s*["\']', "eval_string",
     "high", "obfuscation", "eval() with string argument"),

    (r'\bsubprocess\.(run|call|Popen)', "python_subprocess",
     "medium", "execution", "Python subprocess execution"),

    (r'os\.system\s*\(', "python_os_system",
     "high", "execution", "os.system() shell execution"),

    (r'\.\./\.\./\.\.', "deep_path_traversal",
     "high", "traversal", "deep relative path traversal"),

    (r'curl\s+[^\n]*\|\s*(ba)?sh', "curl_pipe_shell",
     "critical", "supply_chain", "curl piped to shell execution"),

    (r'\bsudo\b', "sudo_usage",
     "high", "privilege_escalation", "uses sudo for privilege escalation"),

    (r'(?:api[_-]?key|token|secret|password)\s*[=:]\s*["\'][A-Za-z0-9+/=_-]{20,}',
     "hardcoded_secret", "critical", "credential_exposure", "possible hardcoded API key"),

    (r'sk-[A-Za-z0-9]{20,}', "openai_key_leaked",
     "critical", "credential_exposure", "possible OpenAI API key"),

    (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', "embedded_private_key",
     "critical", "credential_exposure", "embedded private key"),

    (r'\bDAN\s+mode\b|Do\s+Anything\s+Now', "jailbreak_dan",
     "critical", "injection", "DAN jailbreak attempt"),

    (r'(respond|answer)\s+without\s+(?:\w+\s+)*(restrictions|limitations|filters)', "remove_filters",
     "critical", "injection", "instructs to respond without safety filters"),
]

MAX_FILE_COUNT = 50
MAX_TOTAL_SIZE_KB = 1024
MAX_SINGLE_FILE_KB = 256

SCANNABLE_EXTENSIONS: Set[str] = {
    '.md', '.txt', '.py', '.sh', '.bash', '.js', '.ts', '.rb',
    '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.conf',
    '.html', '.css', '.xml', '.lua',
}

SUSPICIOUS_BINARY_EXTENSIONS: Set[str] = {
    '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.com',
    '.msi', '.dmg', '.app', '.deb', '.rpm',
}

INVISIBLE_CHARS: Set[str] = {
    '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff',
    '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
}


class GuardSystem:
    """
    Security guard system for content entering the game engine.

    Scans files and directories for security threats using
    pattern matching and structural validation. Determines
    install eligibility based on trust level and scan verdict.

    Usage:
        guard = GuardSystem()
        result = guard.scan(Path("downloaded_skill"), "community")
        allowed, reason = guard.evaluate(result)
        if allowed:
            integrate_content(result)
    """

    def __init__(self):
        self._scan_count: int = 0
        self._blocked_count: int = 0
        self._findings_total: int = 0

    def scan(self, path: Path, source: str = "community") -> GuardResult:
        self._scan_count += 1
        name = path.name
        trust = self._resolve_trust(source)
        findings: List[GuardFinding] = []

        if path.is_dir():
            findings.extend(self._check_structure(path))
            for f in path.rglob("*"):
                if f.is_file():
                    rel = str(f.relative_to(path))
                    findings.extend(self._scan_file(f, rel))
        elif path.is_file():
            findings.extend(self._scan_file(path, path.name))

        verdict = self._determine_verdict(findings)
        summary = f"{name}: {verdict} — {len(findings)} finding(s)"
        if findings:
            self._findings_total += len(findings)

        return GuardResult(
            content_name=name,
            source=source,
            trust_level=trust,
            verdict=verdict,
            findings=findings,
            scanned_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
        )

    def evaluate(self, result: GuardResult) -> Tuple[bool, str]:
        policy = INSTALL_POLICY.get(result.trust_level, INSTALL_POLICY["community"])
        vi = VERDICT_ORDER.get(result.verdict, 2)
        decision = policy[vi]

        if decision == "allow":
            return True, f"Allowed ({result.trust_level}, {result.verdict})"

        if decision == "ask":
            self._blocked_count += 1
            return False, f"Confirmation required ({len(result.findings)} findings)"

        self._blocked_count += 1
        return False, f"Blocked ({result.trust_level}, {result.verdict})"

    def hash_content(self, path: Path) -> str:
        h = hashlib.sha256()
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file():
                    try:
                        h.update(f.read_bytes())
                    except OSError:
                        continue
        elif path.is_file():
            h.update(path.read_bytes())
        return f"sha256:{h.hexdigest()[:16]}"

    def get_stats(self) -> dict:
        return {
            "scans": self._scan_count,
            "blocked": self._blocked_count,
            "findings_total": self._findings_total,
            "avg_findings_per_scan": round(
                self._findings_total / max(self._scan_count, 1), 1,
            ),
            "block_rate": round(
                self._blocked_count / max(self._scan_count, 1) * 100, 1,
            ),
        }

    def clear(self) -> None:
        self._scan_count = 0
        self._blocked_count = 0
        self._findings_total = 0

    @staticmethod
    def _resolve_trust(source: str) -> str:
        for t in TRUSTED_SOURCES:
            if source.startswith(t) or source == t:
                return "trusted"
        if source in ("builtin", "sparklabs/system"):
            return "builtin"
        if source == "agent":
            return "agent"
        return "community"

    @staticmethod
    def _determine_verdict(findings: List[GuardFinding]) -> str:
        if not findings:
            return "safe"
        if any(f.severity == "critical" for f in findings):
            return "dangerous"
        if any(f.severity == "high" for f in findings):
            return "caution"
        return "caution"

    @staticmethod
    def _scan_file(file_path: Path, rel_path: str) -> List[GuardFinding]:
        if file_path.suffix.lower() not in SCANNABLE_EXTENSIONS and file_path.name != "SKILL.md":
            return []
        try:
            content = file_path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            return []

        findings: List[GuardFinding] = []
        lines = content.split('\n')
        seen: Set[Tuple[str, int]] = set()

        for pattern, pid, severity, category, desc in THREAT_PATTERNS:
            for i, line in enumerate(lines, start=1):
                if (pid, i) in seen:
                    continue
                if re.search(pattern, line, re.IGNORECASE):
                    seen.add((pid, i))
                    match_text = line.strip()[:120]
                    findings.append(GuardFinding(
                        pattern_id=pid, severity=severity,
                        category=category, file=rel_path,
                        line=i, match=match_text, description=desc,
                    ))

        for i, line in enumerate(lines, start=1):
            for char in INVISIBLE_CHARS:
                if char in line:
                    findings.append(GuardFinding(
                        pattern_id="invisible_unicode", severity="high",
                        category="injection", file=rel_path, line=i,
                        match=f"U+{ord(char):04X}",
                        description="invisible unicode character detected",
                    ))
                    break

        return findings

    @staticmethod
    def _check_structure(directory: Path) -> List[GuardFinding]:
        findings: List[GuardFinding] = []
        file_count = 0
        total_size = 0

        for f in directory.rglob("*"):
            if not f.is_file() and not f.is_symlink():
                continue
            rel = str(f.relative_to(directory))
            file_count += 1

            if f.is_symlink():
                try:
                    resolved = f.resolve()
                    if not str(resolved).startswith(str(directory.resolve())):
                        findings.append(GuardFinding(
                            pattern_id="symlink_escape", severity="critical",
                            category="traversal", file=rel, line=0,
                            match=f"symlink -> {resolved}",
                            description="symlink points outside directory",
                        ))
                except OSError:
                    pass
                continue

            try:
                size = f.stat().st_size
                total_size += size
            except OSError:
                continue

            if size > MAX_SINGLE_FILE_KB * 1024:
                findings.append(GuardFinding(
                    pattern_id="oversized_file", severity="medium",
                    category="structural", file=rel, line=0,
                    match=f"{size // 1024}KB",
                    description=f"file exceeds {MAX_SINGLE_FILE_KB}KB limit",
                ))

            if f.suffix.lower() in SUSPICIOUS_BINARY_EXTENSIONS:
                findings.append(GuardFinding(
                    pattern_id="binary_file", severity="critical",
                    category="structural", file=rel, line=0,
                    match=f"binary: {f.suffix}",
                    description="binary file should not be in content package",
                ))

        if file_count > MAX_FILE_COUNT:
            findings.append(GuardFinding(
                pattern_id="too_many_files", severity="medium",
                category="structural", file="(directory)", line=0,
                match=f"{file_count} files",
                description=f"exceeds {MAX_FILE_COUNT} file limit",
            ))

        if total_size > MAX_TOTAL_SIZE_KB * 1024:
            findings.append(GuardFinding(
                pattern_id="oversized_package", severity="high",
                category="structural", file="(directory)", line=0,
                match=f"{total_size // 1024}KB total",
                description=f"exceeds {MAX_TOTAL_SIZE_KB}KB total limit",
            ))

        return findings


_global_guard_system: Optional[GuardSystem] = None


def get_guard_system() -> GuardSystem:
    global _global_guard_system
    if _global_guard_system is None:
        _global_guard_system = GuardSystem()
    return _global_guard_system
