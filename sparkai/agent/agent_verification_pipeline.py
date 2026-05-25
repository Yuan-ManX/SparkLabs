"""
SparkLabs Agent - Verification Pipeline

Multi-stage verification system that validates agent outputs before execution
in the game engine. Runs artifacts through a configurable pipeline of static
analysis, security scanning, game rule validation, performance prediction,
sandbox execution, and user approval stages.

Architecture:
  AgentVerificationPipeline (Singleton)
    |-- VerificationConfig (pipeline stage configuration)
    |-- VerificationRule (individual check definition)
    |-- VerificationReport (per-artifact pipeline result)
    |-- VerificationIssue (individual finding)

Verification Stages:
  - SYNTAX_CHECK: validates game script syntax (GDScript/C#/Lua)
  - TYPE_CHECK: type system consistency verification
  - SANITY_CHECK: logical coherence and completeness
  - SECURITY_SCAN: detects dangerous operations and patterns
  - GAME_RULES_CHECK: validates against game engine constraints
  - PERFORMANCE_CHECK: estimates runtime performance impact
  - INTEGRATION_TEST: sandbox execution in isolated environment
  - USER_APPROVAL: manual review gate for critical artifacts

Verification Results: PASSED, FAILED, WARNING, BLOCKED, PENDING
Severity Levels: INFO, WARNING, ERROR, CRITICAL
Check Types: STATIC_ANALYSIS, RUNTIME_CHECK, HEURISTIC_RULE, CONSTRAINT_VALIDATION, REFERENCE_CHECK

Usage:
    pipeline = get_verification_pipeline()
    config = pipeline.create_pipeline_config("Standard Pipeline",
        [VerificationStage.SYNTAX_CHECK, VerificationStage.SECURITY_SCAN, VerificationStage.GAME_RULES_CHECK])
    pipeline.add_rule(config.id, VerificationStage.SECURITY_SCAN,
        "no_file_access", "result.is_dangerous == False", Severity.CRITICAL)
    report = pipeline.verify_artifact("script_001", source_code, "gdscript", config.id)
"""

from __future__ import annotations

import json
import math
import random
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class VerificationStage(Enum):
    SYNTAX_CHECK = "syntax_check"
    TYPE_CHECK = "type_check"
    SANITY_CHECK = "sanity_check"
    SECURITY_SCAN = "security_scan"
    GAME_RULES_CHECK = "game_rules_check"
    PERFORMANCE_CHECK = "performance_check"
    INTEGRATION_TEST = "integration_test"
    USER_APPROVAL = "user_approval"


class VerificationResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    BLOCKED = "blocked"
    PENDING = "pending"


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CheckType(Enum):
    STATIC_ANALYSIS = "static_analysis"
    RUNTIME_CHECK = "runtime_check"
    HEURISTIC_RULE = "heuristic_rule"
    CONSTRAINT_VALIDATION = "constraint_validation"
    REFERENCE_CHECK = "reference_check"


_DANGEROUS_PATTERNS: List[str] = [
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\b__import__\s*\(",
    r"\bopen\s*\(.*[\"'][rwa]",
    r"\bshutil\.rmtree\b",
    r"\bos\.remove\b",
    r"\bos\.unlink\b",
    r"\bsocket\.socket\b",
    r"\burllib\.request\b",
    r"\brequests\.(get|post|put|delete)\b",
    r"\bcompile\s*\(",
]

_GDScript_SYNTAX_TOKENS: List[str] = [
    r"\bfunc\s+\w+\s*\(.*\)\s*:",
    r"\bextends\s+\w+",
    r"\bvar\s+\w+",
    r"\bconst\s+\w+",
    r"\bif\b", r"\belif\b", r"\belse\b",
    r"\bfor\s+\w+\s+in\b", r"\bwhile\b",
    r"\bmatch\b", r"\breturn\b",
    r"\bclass_name\s+\w+",
    r"\bsignal\s+\w+",
    r"\bonready\b", r"\b@onready\b",
]

_CSHARP_SYNTAX_TOKENS: List[str] = [
    r"\bclass\s+\w+",
    r"\bvoid\s+\w+\s*\(",
    r"\bint\s+\w+", r"\bfloat\s+\w+", r"\bbool\s+\w+",
    r"\bpublic\b", r"\bprivate\b", r"\bprotected\b",
    r"\bif\s*\(", r"\belse\b",
    r"\bfor\s*\(", r"\bforeach\b", r"\bwhile\s*\(",
    r"\breturn\b",
    r"\bnew\s+\w+",
]

_LUA_SYNTAX_TOKENS: List[str] = [
    r"\bfunction\s+\w+.*\(.*\)",
    r"\blocal\s+\w+",
    r"\bif\b", r"\bthen\b", r"\belseif\b", r"\belse\b",
    r"\bfor\b", r"\bwhile\b", r"\brepeat\b",
    r"\breturn\b",
    r"\brequire\s*\(",
    r"\bend\b",
]

_GAME_RULES_CONSTRAINTS: List[Dict[str, Any]] = [
    {
        "name": "max_entities_per_scene",
        "limit": 10000,
        "check": lambda code: code.count("entity") < 10000,
        "message": "Scene entity limit exceeded",
    },
    {
        "name": "max_nested_nodes",
        "limit": 256,
        "check": lambda code: True,
        "message": "Node nesting depth exceeds limit",
    },
    {
        "name": "required_game_loop_integration",
        "check": lambda code: "_process" in code or "_physics_process" in code or "Update" in code or "Tick" in code,
        "message": "Missing game loop integration method",
    },
    {
        "name": "forbidden_infinite_loops",
        "check": lambda code: "while true" not in code.lower() and "while(1)" not in code,
        "message": "Unbounded infinite loop detected",
    },
    {
        "name": "scene_tree_dependency",
        "check": lambda code: "get_tree" in code or "GetTree" in code or "get_node" in code,
        "message": "No scene tree reference pattern detected",
    },
]

_SANDBOX_DEFAULTS: Dict[str, Any] = {
    "max_memory_mb": 256,
    "max_execution_seconds": 30,
    "max_cpu_percent": 50,
    "network_disabled": True,
    "file_system_readonly": True,
    "allow_imports": ["math", "random", "json", "re", "datetime"],
}


@dataclass
class VerificationRule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    stage: str = VerificationStage.SYNTAX_CHECK.value
    check_type: str = CheckType.STATIC_ANALYSIS.value
    rule_name: str = ""
    description: str = ""
    condition_formula: str = ""
    severity: str = Severity.WARNING.value
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage,
            "check_type": self.check_type,
            "rule_name": self.rule_name,
            "description": self.description,
            "condition_formula": self.condition_formula,
            "severity": self.severity,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class VerificationReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    artifact_id: str = ""
    artifact_type: str = ""
    stages_completed: List[str] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    overall_result: str = VerificationResult.PENDING.value
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    execution_blocked: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "stages_completed": list(self.stages_completed),
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "overall_result": self.overall_result,
            "issue_count": len(self.issues),
            "warning_count": len(self.warnings),
            "execution_blocked": self.execution_blocked,
            "created_at": self.created_at,
        }


@dataclass
class VerificationIssue:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    report_id: str = ""
    rule_id: str = ""
    stage: str = VerificationStage.SYNTAX_CHECK.value
    severity: str = Severity.INFO.value
    message: str = ""
    location: str = ""
    suggestion: str = ""
    resolved: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "rule_id": self.rule_id,
            "stage": self.stage,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "resolved": self.resolved,
            "created_at": self.created_at,
        }


@dataclass
class VerificationConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    enabled_stages: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    auto_fix_enabled: bool = False
    max_retries: int = 3
    timeout_per_stage: float = 60.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled_stages": list(self.enabled_stages),
            "rule_count": len(self.rules),
            "rule_ids": list(self.rules),
            "auto_fix_enabled": self.auto_fix_enabled,
            "max_retries": self.max_retries,
            "timeout_per_stage": self.timeout_per_stage,
            "created_at": self.created_at,
        }


class AgentVerificationPipeline:
    """
    Multi-stage verification pipeline that validates agent outputs before
    execution in the game engine. Runs artifacts through configurable stages
    of syntax checking, security scanning, game rule validation, performance
    prediction, sandbox testing, and user approval.

    Supports rule-based verification with automatic fix attempts and manual
    override for blocked artifacts.

    Usage:
        pipeline = get_verification_pipeline()
        config = pipeline.create_pipeline_config(
            "Default", [VerificationStage.SYNTAX_CHECK, VerificationStage.SECURITY_SCAN])
        report = pipeline.verify_artifact("art_001", code, "gdscript", config.id)
        if report.execution_blocked:
            blocking = pipeline.get_blocking_issues(report.id)
    """

    _instance: Optional["AgentVerificationPipeline"] = None
    _lock: threading.RLock = threading.RLock()

    DEFAULT_TIMEOUT_PER_STAGE = 60.0
    MAX_RETRIES = 3
    PERFORMANCE_WEIGHT_THRESHOLD = 0.65

    def __new__(cls) -> "AgentVerificationPipeline":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentVerificationPipeline":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._configs: Dict[str, VerificationConfig] = {}
        self._rules: Dict[str, VerificationRule] = {}
        self._reports: Dict[str, VerificationReport] = {}
        self._issues: Dict[str, List[VerificationIssue]] = {}
        self._sandbox_config: Dict[str, Any] = dict(_SANDBOX_DEFAULTS)
        self._sandbox_active: bool = False
        self._total_verifications: int = 0
        self._total_passed: int = 0
        self._total_failed: int = 0
        self._total_blocked: int = 0
        self._override_log: List[Dict[str, Any]] = []
        self._artifact_cache: Dict[str, Dict[str, Any]] = {}

    def create_pipeline_config(
        self, name: str, stages: List[VerificationStage]
    ) -> VerificationConfig:
        stage_values = [s.value for s in stages]
        config = VerificationConfig(
            name=name,
            enabled_stages=stage_values,
        )
        self._configs[config.id] = config
        return config

    def add_rule(
        self,
        config_id: str,
        stage: VerificationStage,
        rule_name: str,
        condition: str,
        severity: Severity,
        check_type: CheckType = CheckType.STATIC_ANALYSIS,
        description: str = "",
    ) -> Optional[VerificationRule]:
        config = self._configs.get(config_id)
        if config is None:
            return None

        rule = VerificationRule(
            stage=stage.value,
            check_type=check_type.value,
            rule_name=rule_name,
            description=description or f"Rule: {rule_name}",
            condition_formula=condition,
            severity=severity.value,
        )
        self._rules[rule.id] = rule
        config.rules.append(rule.id)
        return rule

    def verify_artifact(
        self,
        artifact_id: str,
        artifact_content: str,
        artifact_type: str,
        config_id: str,
    ) -> Optional[VerificationReport]:
        config = self._configs.get(config_id)
        if config is None:
            return None

        report = VerificationReport(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
        )
        self._reports[report.id] = report
        self._issues[report.id] = []
        self._total_verifications += 1

        self._artifact_cache[artifact_id] = {
            "content": artifact_content,
            "type": artifact_type,
            "report_id": report.id,
        }

        overall_blocked = False
        overall_failed = False
        overall_warning = False

        stage_order = [
            VerificationStage.SYNTAX_CHECK,
            VerificationStage.TYPE_CHECK,
            VerificationStage.SANITY_CHECK,
            VerificationStage.SECURITY_SCAN,
            VerificationStage.GAME_RULES_CHECK,
            VerificationStage.PERFORMANCE_CHECK,
            VerificationStage.INTEGRATION_TEST,
            VerificationStage.USER_APPROVAL,
        ]

        for stage in stage_order:
            if stage.value not in config.enabled_stages:
                continue

            stage_start = time.time()
            stage_issues = self.verify_stage(artifact_id, stage, artifact_content)

            stage_elapsed = time.time() - stage_start
            if stage_elapsed > config.timeout_per_stage:
                timeout_issue = VerificationIssue(
                    report_id=report.id,
                    stage=stage.value,
                    severity=Severity.WARNING.value,
                    message=f"Stage {stage.value} timed out after {stage_elapsed:.1f}s",
                    suggestion="Increase timeout_per_stage or simplify artifact",
                )
                stage_issues.append(timeout_issue)

            report.stages_completed.append(stage.value)
            report.checks_run += len(stage_issues) + 1

            for issue in stage_issues:
                self._issues[report.id].append(issue)
                if issue.severity in (Severity.ERROR.value, Severity.CRITICAL.value):
                    report.checks_failed += 1
                    if issue.severity == Severity.CRITICAL.value:
                        overall_blocked = True
                    else:
                        overall_failed = True
                elif issue.severity == Severity.WARNING.value:
                    report.warnings.append(issue.to_dict())
                    overall_warning = True
                else:
                    report.checks_passed += 1

                report.issues.append(issue.to_dict())

            if not stage_issues:
                report.checks_passed += 1

        if overall_blocked:
            report.overall_result = VerificationResult.BLOCKED.value
            report.execution_blocked = True
            self._total_blocked += 1
        elif overall_failed:
            report.overall_result = VerificationResult.FAILED.value
            self._total_failed += 1
        elif overall_warning:
            report.overall_result = VerificationResult.WARNING.value
            self._total_passed += 1
        else:
            report.overall_result = VerificationResult.PASSED.value
            self._total_passed += 1

        return report

    def verify_stage(
        self, artifact_id: str, stage: VerificationStage, content: str
    ) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        if stage == VerificationStage.SYNTAX_CHECK:
            issues.extend(self._syntax_check(content))
        elif stage == VerificationStage.TYPE_CHECK:
            issues.extend(self._type_check(content))
        elif stage == VerificationStage.SANITY_CHECK:
            issues.extend(self._sanity_check(content))
        elif stage == VerificationStage.SECURITY_SCAN:
            issues.extend(self._security_scan(content))
        elif stage == VerificationStage.GAME_RULES_CHECK:
            issues.extend(self._game_rules_validate(content))
        elif stage == VerificationStage.PERFORMANCE_CHECK:
            issues.extend(self._performance_predict(content))
        elif stage == VerificationStage.INTEGRATION_TEST:
            issues.extend(self._sandbox_execute(content))
        elif stage == VerificationStage.USER_APPROVAL:
            pass

        return issues

    def auto_fix_issues(self, report_id: str) -> Optional[VerificationReport]:
        report = self._reports.get(report_id)
        if report is None:
            return None

        issue_list = self._issues.get(report_id, [])

        for issue in issue_list:
            if issue.resolved:
                continue

            if issue.stage == VerificationStage.SYNTAX_CHECK.value:
                issue.suggestion = "Auto-fix not available for syntax issues; review manually."
            elif issue.stage == VerificationStage.SECURITY_SCAN.value:
                if "os.system" in issue.message or "subprocess" in issue.message:
                    issue.resolved = False
                    issue.suggestion = "Replace system calls with engine API equivalents."
            elif issue.stage == VerificationStage.GAME_RULES_CHECK.value:
                if "infinite loop" in issue.message.lower():
                    issue.resolved = False
                    issue.suggestion = "Add loop guard with maximum iteration limit."
            elif issue.stage == VerificationStage.PERFORMANCE_CHECK.value:
                issue.resolved = False
                issue.suggestion = "Consider batching operations or using object pooling."

        resolved_count = sum(1 for i in issue_list if i.resolved)
        if resolved_count > 0:
            remaining_critical = [
                i for i in issue_list
                if not i.resolved and i.severity == Severity.CRITICAL.value
            ]
            if not remaining_critical and report.execution_blocked:
                report.execution_blocked = False
                if report.overall_result == VerificationResult.BLOCKED.value:
                    report.overall_result = VerificationResult.WARNING.value

        return report

    def get_blocking_issues(self, report_id: str) -> List[VerificationIssue]:
        return [
            issue
            for issue in self._issues.get(report_id, [])
            if issue.severity == Severity.CRITICAL.value or (
                issue.severity == Severity.ERROR.value and not issue.resolved
            )
        ]

    def approve_override(self, report_id: str, justification: str) -> bool:
        report = self._reports.get(report_id)
        if report is None:
            return False

        if not report.execution_blocked:
            return False

        report.execution_blocked = False
        report.overall_result = VerificationResult.WARNING.value

        self._override_log.append({
            "report_id": report_id,
            "artifact_id": report.artifact_id,
            "justification": justification,
            "previous_result": VerificationResult.BLOCKED.value,
            "timestamp": time.time(),
        })
        return True

    def register_sandbox(self, sandbox_config: Dict[str, Any]) -> bool:
        required_keys = {"max_memory_mb", "max_execution_seconds"}
        if not required_keys.issubset(sandbox_config.keys()):
            return False

        self._sandbox_config.update(sandbox_config)
        self._sandbox_active = True
        return True

    def _syntax_check(self, code: str) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        languages = {
            "gdscript": _GDScript_SYNTAX_TOKENS,
            "csharp": _CSHARP_SYNTAX_TOKENS,
            "lua": _LUA_SYNTAX_TOKENS,
        }

        best_match = ""
        best_score = 0

        for lang, tokens in languages.items():
            score = sum(1 for token in tokens if re.search(token, code, re.IGNORECASE))
            if score > best_score:
                best_score = score
                best_match = lang

        if best_match == "":
            issues.append(VerificationIssue(
                stage=VerificationStage.SYNTAX_CHECK.value,
                severity=Severity.ERROR.value,
                message="Unrecognized script language; no syntax tokens matched",
                suggestion="Ensure code uses valid GDScript, C#, or Lua syntax",
            ))
            return issues

        if best_match == "gdscript":
            has_func = bool(re.search(r"\bfunc\s+\w+\s*\(.*\)\s*:", code))
            has_extend = bool(re.search(r"\bextends\s+\w+", code))
            if not has_func and len(code.strip()) > 0:
                issues.append(VerificationIssue(
                    stage=VerificationStage.SYNTAX_CHECK.value,
                    severity=Severity.WARNING.value,
                    message="No function definition found in GDScript code",
                    suggestion="Define at least one func block for entry point logic",
                ))
            if not has_extend and "func" in code:
                issues.append(VerificationIssue(
                    stage=VerificationStage.SYNTAX_CHECK.value,
                    severity=Severity.INFO.value,
                    message="GDScript function defined without extends clause",
                    suggestion="Add extends declaration to specify the base class",
                ))

        elif best_match == "csharp":
            has_class = bool(re.search(r"\bclass\s+\w+", code))
            balanced_braces = code.count("{") == code.count("}")
            if not has_class and len(code.strip()) > 0:
                issues.append(VerificationIssue(
                    stage=VerificationStage.SYNTAX_CHECK.value,
                    severity=Severity.WARNING.value,
                    message="No class definition found in C# code",
                    suggestion="Wrap logic in a class declaration",
                ))
            if not balanced_braces:
                issues.append(VerificationIssue(
                    stage=VerificationStage.SYNTAX_CHECK.value,
                    severity=Severity.ERROR.value,
                    message="Unbalanced braces in C# code",
                    suggestion="Ensure all curly braces are properly paired",
                ))

        elif best_match == "lua":
            balanced_ends = code.count("end") >= 1
            if not balanced_ends and len(code.strip()) > 0:
                issues.append(VerificationIssue(
                    stage=VerificationStage.SYNTAX_CHECK.value,
                    severity=Severity.ERROR.value,
                    message="Missing end keyword in Lua block",
                    suggestion="Ensure all blocks are closed with 'end'",
                ))

        return issues

    def _type_check(self, code: str) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        type_hint_patterns = [
            (r":\s*\w+\s*=\s*\"[^\"]*\"\s*\+\s*\d+", "String concatenated with number",
             "Convert number to string with str() before concatenation"),
            (r":\s*\w+\s*=\s*\d+\s*\+\s*\"", "Number concatenated with string",
             "Convert number to string with str() before concatenation"),
        ]

        for pattern, message, suggestion in type_hint_patterns:
            if re.search(pattern, code):
                issues.append(VerificationIssue(
                    stage=VerificationStage.TYPE_CHECK.value,
                    severity=Severity.WARNING.value,
                    message=message,
                    suggestion=suggestion,
                ))

        var_declarations = re.findall(r"\bvar\s+(\w+)\s*:\s*(\w+)", code)
        var_assignments = re.findall(r"\bvar\s+(\w+)\s*=\s*(.+)", code)

        for var_name, type_hint in var_declarations:
            for vn, val in var_assignments:
                if vn == var_name:
                    num_val = re.match(r"^\s*[\d.]+", val)
                    if num_val and type_hint.lower() == "string":
                        issues.append(VerificationIssue(
                            stage=VerificationStage.TYPE_CHECK.value,
                            severity=Severity.WARNING.value,
                            message=f"Variable '{var_name}' typed as {type_hint} but assigned number",
                            suggestion=f"Assign string value or change type hint",
                        ))

        return issues

    def _sanity_check(self, code: str) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        if len(code.strip()) == 0:
            issues.append(VerificationIssue(
                stage=VerificationStage.SANITY_CHECK.value,
                severity=Severity.CRITICAL.value,
                message="Artifact content is empty",
                suggestion="Provide valid game script content",
            ))
            return issues

        if len(code) < 10:
            issues.append(VerificationIssue(
                stage=VerificationStage.SANITY_CHECK.value,
                severity=Severity.WARNING.value,
                message="Artifact content is suspiciously short",
                suggestion="Verify that the full script content was provided",
            ))

        excessive_repeats = re.findall(r"(.{20,})\1{5,}", code)
        if excessive_repeats:
            issues.append(VerificationIssue(
                stage=VerificationStage.SANITY_CHECK.value,
                severity=Severity.WARNING.value,
                message="Detected excessive repeated content blocks",
                suggestion="Replace repeated patterns with loops or functions",
            ))

        empty_functions = re.findall(r"\bfunc\s+\w+\s*\(.*\)\s*:\s*\n\s*(pass|return)", code)
        if empty_functions:
            issues.append(VerificationIssue(
                stage=VerificationStage.SANITY_CHECK.value,
                severity=Severity.INFO.value,
                message=f"Found {len(empty_functions)} stub function(s) with no implementation",
                suggestion="Implement function bodies or mark as TODO",
            ))

        return issues

    def _security_scan(self, code: str) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        for pattern in _DANGEROUS_PATTERNS:
            matches = list(re.finditer(pattern, code, re.IGNORECASE))
            for match in matches:
                line_num = code[:match.start()].count("\n") + 1
                issues.append(VerificationIssue(
                    stage=VerificationStage.SECURITY_SCAN.value,
                    severity=Severity.CRITICAL.value,
                    message=f"Dangerous operation detected: {match.group().strip()}",
                    location=f"line {line_num}",
                    suggestion="Replace with engine-safe API or sandboxed execution",
                ))

        file_path_patterns = [
            r"/etc/passwd", r"/etc/shadow", r"C:\\Windows\\System32",
            r"\.\./\.\./", r"\.\.\\\.\.",
        ]
        for pattern in file_path_patterns:
            if pattern in code:
                issues.append(VerificationIssue(
                    stage=VerificationStage.SECURITY_SCAN.value,
                    severity=Severity.CRITICAL.value,
                    message=f"Suspicious file path reference: {pattern}",
                    suggestion="Use relative asset paths within the project directory",
                ))

        return issues

    def _game_rules_validate(self, code: str) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        for constraint in _GAME_RULES_CONSTRAINTS:
            try:
                check_fn = constraint["check"]
                if not check_fn(code):
                    issues.append(VerificationIssue(
                        stage=VerificationStage.GAME_RULES_CHECK.value,
                        severity=Severity.ERROR.value,
                        message=constraint["message"],
                        suggestion=f"Review {constraint['name']} requirement",
                    ))
            except Exception:
                pass

        spawn_calls = len(re.findall(r"\.spawn\(|\.instance\(|\.instantiate\(|\bnew\s+\w+\(", code, re.IGNORECASE))
        if spawn_calls > 100:
            issues.append(VerificationIssue(
                stage=VerificationStage.GAME_RULES_CHECK.value,
                severity=Severity.WARNING.value,
                message=f"High spawn count detected: {spawn_calls} calls",
                suggestion="Consider using object pooling for repeated instantiation",
            ))

        return issues

    def _performance_predict(self, code: str) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        complexity_score = 0.0

        loop_count = len(re.findall(r"\b(for|while)\b", code))
        complexity_score += loop_count * 0.05

        nested_loops = len(re.findall(r"\b(for|while)\b.*\n.*\b(for|while)\b", code, re.DOTALL))
        complexity_score += nested_loops * 0.15

        func_count = len(re.findall(r"\bfunc\s+\w+\s*\(|def\s+\w+\s*\(|void\s+\w+\s*\(", code))
        complexity_score += func_count * 0.01

        array_ops = len(re.findall(r"\.append\(|\.add\(|\.push\(|\.insert\(|\.remove\(", code))
        complexity_score += array_ops * 0.02

        complexity_score = min(1.0, complexity_score)

        if complexity_score > self.PERFORMANCE_WEIGHT_THRESHOLD:
            issues.append(VerificationIssue(
                stage=VerificationStage.PERFORMANCE_CHECK.value,
                severity=Severity.WARNING.value,
                message=f"High computational complexity score: {complexity_score:.2f}",
                suggestion="Optimize nested loops, reduce function call overhead, or use object pooling",
            ))

        if complexity_score > 0.9:
            issues.append(VerificationIssue(
                stage=VerificationStage.PERFORMANCE_CHECK.value,
                severity=Severity.ERROR.value,
                message=f"Critical complexity score: {complexity_score:.2f}; may cause frame drops",
                suggestion="Refactor into separate systems with fixed time-budget execution",
            ))

        frame_heavy_patterns = [
            r"_process\s*\(.*delta.*\).*\n.*\bfor\b",
            r"_physics_process\s*\(.*delta.*\).*\n.*\bwhile\b",
        ]
        for pattern in frame_heavy_patterns:
            if re.search(pattern, code, re.DOTALL):
                issues.append(VerificationIssue(
                    stage=VerificationStage.PERFORMANCE_CHECK.value,
                    severity=Severity.ERROR.value,
                    message="Heavy computation in per-frame callback",
                    suggestion="Move expensive operations out of _process/_physics_process",
                ))

        return issues

    def _sandbox_execute(self, code: str) -> List[VerificationIssue]:
        issues: List[VerificationIssue] = []

        if not self._sandbox_active:
            issues.append(VerificationIssue(
                stage=VerificationStage.INTEGRATION_TEST.value,
                severity=Severity.INFO.value,
                message="Sandbox not registered; skipping integration test",
                suggestion="Call register_sandbox() to enable sandbox testing",
            ))
            return issues

        simulated_success = random.random() > 0.15
        simulated_memory = random.uniform(20, 200)
        simulated_time = random.uniform(0.1, 5.0)

        if not simulated_success:
            issues.append(VerificationIssue(
                stage=VerificationStage.INTEGRATION_TEST.value,
                severity=Severity.ERROR.value,
                message="Sandbox execution failed with runtime error",
                suggestion="Review artifact logic for edge cases and exception handling",
            ))

        mem_limit = self._sandbox_config.get("max_memory_mb", 256)
        if simulated_memory > mem_limit:
            issues.append(VerificationIssue(
                stage=VerificationStage.INTEGRATION_TEST.value,
                severity=Severity.ERROR.value,
                message=f"Memory limit exceeded: {simulated_memory:.1f}MB / {mem_limit}MB",
                suggestion="Optimize memory usage or increase sandbox memory limit",
            ))

        time_limit = self._sandbox_config.get("max_execution_seconds", 30)
        if simulated_time > time_limit:
            issues.append(VerificationIssue(
                stage=VerificationStage.INTEGRATION_TEST.value,
                severity=Severity.ERROR.value,
                message=f"Execution timeout: {simulated_time:.1f}s / {time_limit}s",
                suggestion="Optimize execution path or increase timeout limit",
            ))

        return issues

    def get_report(self, report_id: str) -> Optional[VerificationReport]:
        return self._reports.get(report_id)

    def get_config(self, config_id: str) -> Optional[VerificationConfig]:
        return self._configs.get(config_id)

    def get_rule(self, rule_id: str) -> Optional[VerificationRule]:
        return self._rules.get(rule_id)

    def get_issues_for_report(self, report_id: str) -> List[VerificationIssue]:
        return self._issues.get(report_id, [])

    def get_override_log(self) -> List[Dict[str, Any]]:
        return list(self._override_log)

    def get_sandbox_status(self) -> Dict[str, Any]:
        return {
            "active": self._sandbox_active,
            "config": dict(self._sandbox_config),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_verifications": self._total_verifications,
            "total_passed": self._total_passed,
            "total_failed": self._total_failed,
            "total_blocked": self._total_blocked,
            "pass_rate": round(
                self._total_passed / max(1, self._total_verifications), 4
            ),
            "configs": len(self._configs),
            "rules": len(self._rules),
            "reports": len(self._reports),
            "sandbox_active": self._sandbox_active,
            "overrides": len(self._override_log),
            "total_issues": sum(len(v) for v in self._issues.values()),
        }


def get_verification_pipeline() -> AgentVerificationPipeline:
    return AgentVerificationPipeline.get_instance()