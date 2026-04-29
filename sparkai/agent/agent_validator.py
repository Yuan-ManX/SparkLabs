"""
SparkAI Agent - Validator Engine

A comprehensive validation system for the AI-native game engine that
checks code quality, asset integrity, game rules, and configuration
consistency. Provides rule-based and pattern-based validation with
detailed reports and auto-fix suggestions.

Architecture:
  ValidatorEngine
    |-- ValidationRule (individual validation check)
    |-- ValidationReport (comprehensive validation results)
    |-- ValidationIssue (individual issue with severity and fix)
    |-- RuleSet (grouped validation rules)
    |-- AutoFixer (automatic issue resolution)
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    CODE_STYLE = "code_style"
    CODE_LOGIC = "code_logic"
    ASSET_INTEGRITY = "asset_integrity"
    GAME_RULES = "game_rules"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    NAMING = "naming"
    STRUCTURE = "structure"


class RuleScope(Enum):
    GLOBAL = "global"
    PROJECT = "project"
    FILE = "file"
    ASSET = "asset"
    SCENE = "scene"
    ENTITY = "entity"


class FixType(Enum):
    AUTO = "auto"
    MANUAL = "manual"
    SUGGESTED = "suggested"
    NONE = "none"


@dataclass
class ValidationIssue:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    rule_id: str = ""
    severity: ValidationSeverity = ValidationSeverity.WARNING
    category: ValidationCategory = ValidationCategory.CODE_STYLE
    message: str = ""
    location: str = ""
    line: Optional[int] = None
    column: Optional[int] = None
    fix_type: FixType = FixType.NONE
    fix_suggestion: str = ""
    fix_data: Optional[Dict[str, Any]] = None
    context: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "location": self.location,
            "line": self.line,
            "column": self.column,
            "fix_type": self.fix_type.value,
            "fix_suggestion": self.fix_suggestion,
            "fix_data": self.fix_data,
            "context": self.context,
            "created_at": self.created_at,
        }


@dataclass
class ValidationRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    category: ValidationCategory = ValidationCategory.CODE_STYLE
    severity: ValidationSeverity = ValidationSeverity.WARNING
    scope: RuleScope = RuleScope.GLOBAL
    pattern: str = ""
    check_fn: Optional[str] = None
    auto_fixable: bool = False
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "scope": self.scope.value,
            "pattern": self.pattern,
            "auto_fixable": self.auto_fixable,
            "enabled": self.enabled,
            "tags": self.tags,
        }


@dataclass
class ValidationReport:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target: str = ""
    target_type: str = ""
    issues: List[ValidationIssue] = field(default_factory=list)
    passed: bool = True
    score: float = 100.0
    duration_ms: float = 0.0
    rules_checked: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target": self.target,
            "target_type": self.target_type,
            "issue_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
            "passed": self.passed,
            "score": self.score,
            "duration_ms": self.duration_ms,
            "rules_checked": self.rules_checked,
            "by_severity": self._severity_counts(),
            "by_category": self._category_counts(),
            "created_at": self.created_at,
        }

    def _severity_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for issue in self.issues:
            counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
        return counts

    def _category_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for issue in self.issues:
            counts[issue.category.value] = counts.get(issue.category.value, 0) + 1
        return counts


@dataclass
class RuleSet:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    rule_ids: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_count": len(self.rule_ids),
            "rule_ids": self.rule_ids,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


class AutoFixer:
    """
    Provides automatic fixes for common validation issues.
    """

    def __init__(self) -> None:
        self._fix_count: int = 0
        self._fix_success: int = 0

    def apply_fix(self, issue: ValidationIssue, content: str) -> Tuple[str, bool]:
        if issue.fix_type != FixType.AUTO:
            return content, False

        self._fix_count += 1
        fixed = False

        if issue.category == ValidationCategory.CODE_STYLE:
            if "trailing whitespace" in issue.message.lower():
                lines = content.split("\n")
                if issue.line and 0 < issue.line <= len(lines):
                    lines[issue.line - 1] = lines[issue.line - 1].rstrip()
                    content = "\n".join(lines)
                    fixed = True

            elif "missing newline" in issue.message.lower():
                if not content.endswith("\n"):
                    content += "\n"
                    fixed = True

            elif "multiple blank lines" in issue.message.lower():
                content = re.sub(r'\n{4,}', '\n\n\n', content)
                fixed = True

        elif issue.category == ValidationCategory.NAMING:
            if "snake_case" in issue.message.lower() and issue.fix_data:
                old_name = issue.fix_data.get("old_name", "")
                new_name = issue.fix_data.get("new_name", "")
                if old_name and new_name:
                    content = content.replace(old_name, new_name)
                    fixed = True

        if fixed:
            self._fix_success += 1
        return content, fixed

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_fixes_attempted": self._fix_count,
            "successful_fixes": self._fix_success,
            "success_rate": self._fix_success / max(self._fix_count, 1),
        }


class ValidatorEngine:
    """
    Central validation system for the SparkLabs AI-native game engine.

    Checks code quality, asset integrity, game rules, and configuration
    consistency with detailed reports and auto-fix suggestions.
    """

    def __init__(self) -> None:
        self._rules: Dict[str, ValidationRule] = {}
        self._rule_sets: Dict[str, RuleSet] = {}
        self._reports: List[ValidationReport] = []
        self._auto_fixer = AutoFixer()
        self._report_count: int = 0
        self._seed_rules()

    def _seed_rules(self) -> None:
        seed_rules = [
            ("no_console_log", "No Console Log", "Avoid console.log in production code",
             ValidationCategory.CODE_STYLE, ValidationSeverity.WARNING, r"console\.log"),
            ("no_debugger", "No Debugger Statement", "Remove debugger statements",
             ValidationCategory.CODE_STYLE, ValidationSeverity.ERROR, r"debugger"),
            ("no_todo", "No TODO Comments", "Resolve TODO comments before release",
             ValidationCategory.CODE_LOGIC, ValidationSeverity.INFO, r"TODO|FIXME|HACK|XXX"),
            ("max_file_lines", "Max File Length", "Files should not exceed 500 lines",
             ValidationCategory.STRUCTURE, ValidationSeverity.WARNING, ""),
            ("trailing_ws", "No Trailing Whitespace", "Remove trailing whitespace",
             ValidationCategory.CODE_STYLE, ValidationSeverity.INFO, r"[ \t]+$"),
            ("naming_snake", "Snake Case Variables", "Use snake_case for variable names",
             ValidationCategory.NAMING, ValidationSeverity.WARNING, ""),
            ("asset_path_valid", "Valid Asset Paths", "Asset paths must reference existing files",
             ValidationCategory.ASSET_INTEGRITY, ValidationSeverity.ERROR, ""),
            ("no_hardcoded_secrets", "No Hardcoded Secrets", "Do not hardcode API keys or secrets",
             ValidationCategory.SECURITY, ValidationSeverity.CRITICAL, r"(api_key|secret|password)\s*=\s*['\"]"),
            ("consistent_indent", "Consistent Indentation", "Use consistent indentation style",
             ValidationCategory.CODE_STYLE, ValidationSeverity.WARNING, ""),
            ("scene_entity_limit", "Scene Entity Limit", "Scenes should not exceed 1000 entities",
             ValidationCategory.PERFORMANCE, ValidationSeverity.WARNING, ""),
        ]

        for rid, name, desc, cat, sev, pattern in seed_rules:
            rule = ValidationRule(
                id=rid,
                name=name,
                description=desc,
                category=cat,
                severity=sev,
                pattern=pattern,
                auto_fixable=rid in ("trailing_ws", "naming_snake"),
            )
            self._rules[rid] = rule

        code_ruleset = RuleSet(
            name="Code Quality",
            description="Rules for code quality and style",
            rule_ids=["no_console_log", "no_debugger", "no_todo", "trailing_ws", "naming_snake", "consistent_indent", "no_hardcoded_secrets"],
        )
        self._rule_sets[code_ruleset.id] = code_ruleset

        asset_ruleset = RuleSet(
            name="Asset Validation",
            description="Rules for asset integrity and paths",
            rule_ids=["asset_path_valid"],
        )
        self._rule_sets[asset_ruleset.id] = asset_ruleset

        perf_ruleset = RuleSet(
            name="Performance Checks",
            description="Rules for performance optimization",
            rule_ids=["max_file_lines", "scene_entity_limit"],
        )
        self._rule_sets[perf_ruleset.id] = perf_ruleset

    def add_rule(
        self,
        name: str,
        description: str = "",
        category: str = "code_style",
        severity: str = "warning",
        scope: str = "global",
        pattern: str = "",
        auto_fixable: bool = False,
        tags: Optional[List[str]] = None,
    ) -> ValidationRule:
        rule = ValidationRule(
            name=name,
            description=description,
            category=ValidationCategory(category),
            severity=ValidationSeverity(severity),
            scope=RuleScope(scope),
            pattern=pattern,
            auto_fixable=auto_fixable,
            tags=tags or [],
        )
        self._rules[rule.id] = rule
        return rule

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        rule = self._rules.get(rule_id)
        if rule:
            return rule.to_dict()
        return None

    def list_rules(
        self,
        category: Optional[ValidationCategory] = None,
        enabled_only: bool = False,
    ) -> List[Dict[str, Any]]:
        rules = list(self._rules.values())
        if category:
            rules = [r for r in rules if r.category == category]
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return [r.to_dict() for r in rules]

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.enabled = enabled
        return True

    def validate_code(
        self,
        content: str,
        file_path: str = "",
        rule_ids: Optional[List[str]] = None,
    ) -> ValidationReport:
        start_time = time.time()
        report = ValidationReport(
            target=file_path or "inline",
            target_type="code",
        )

        rules_to_check = self._get_rules_to_check(rule_ids)

        for rule in rules_to_check:
            if not rule.enabled:
                continue

            if rule.pattern:
                for match in re.finditer(rule.pattern, content, re.MULTILINE):
                    line_num = content[:match.start()].count("\n") + 1
                    issue = ValidationIssue(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        message=f"{rule.name}: found '{match.group()}'",
                        location=file_path,
                        line=line_num,
                        column=match.start() - content.rfind("\n", 0, match.start()),
                        fix_type=FixType.AUTO if rule.auto_fixable else FixType.SUGGESTED,
                        fix_suggestion=rule.description,
                        context=match.group(),
                    )
                    report.issues.append(issue)

            if rule.id == "max_file_lines":
                line_count = content.count("\n") + 1
                if line_count > 500:
                    issue = ValidationIssue(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        message=f"File has {line_count} lines (max 500)",
                        location=file_path,
                        fix_type=FixType.MANUAL,
                        fix_suggestion="Split the file into smaller modules",
                    )
                    report.issues.append(issue)

        report.rules_checked = len(rules_to_check)
        report.passed = not any(
            i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for i in report.issues
        )
        report.score = max(0.0, 100.0 - sum(
            {ValidationSeverity.INFO: 1, ValidationSeverity.WARNING: 5,
             ValidationSeverity.ERROR: 20, ValidationSeverity.CRITICAL: 50}.get(i.severity, 0)
            for i in report.issues
        ))
        report.duration_ms = (time.time() - start_time) * 1000

        self._reports.append(report)
        self._report_count += 1
        return report

    def validate_asset(
        self,
        asset_data: Dict[str, Any],
        rule_ids: Optional[List[str]] = None,
    ) -> ValidationReport:
        start_time = time.time()
        report = ValidationReport(
            target=asset_data.get("name", "unknown"),
            target_type="asset",
        )

        rules_to_check = self._get_rules_to_check(rule_ids)

        for rule in rules_to_check:
            if not rule.enabled:
                continue

            if rule.id == "asset_path_valid":
                path = asset_data.get("path", "")
                if not path:
                    issue = ValidationIssue(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        message="Asset has no path specified",
                        fix_type=FixType.MANUAL,
                        fix_suggestion="Provide a valid file path for the asset",
                    )
                    report.issues.append(issue)

            if rule.id == "scene_entity_limit":
                entity_count = asset_data.get("entity_count", 0)
                if entity_count > 1000:
                    issue = ValidationIssue(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        message=f"Scene has {entity_count} entities (max 1000)",
                        fix_type=FixType.MANUAL,
                        fix_suggestion="Split scene into sub-scenes or use LOD",
                    )
                    report.issues.append(issue)

        report.rules_checked = len(rules_to_check)
        report.passed = not any(
            i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for i in report.issues
        )
        report.score = max(0.0, 100.0 - sum(
            {ValidationSeverity.INFO: 1, ValidationSeverity.WARNING: 5,
             ValidationSeverity.ERROR: 20, ValidationSeverity.CRITICAL: 50}.get(i.severity, 0)
            for i in report.issues
        ))
        report.duration_ms = (time.time() - start_time) * 1000

        self._reports.append(report)
        self._report_count += 1
        return report

    def auto_fix(self, report_id: str, content: str) -> Optional[Dict[str, Any]]:
        report = None
        for r in self._reports:
            if r.id == report_id:
                report = r
                break

        if not report:
            return None

        fixed_content = content
        fixes_applied: List[Dict[str, Any]] = []

        for issue in report.issues:
            if issue.fix_type == FixType.AUTO:
                new_content, success = self._auto_fixer.apply_fix(issue, fixed_content)
                if success:
                    fixed_content = new_content
                    fixes_applied.append({
                        "issue_id": issue.id,
                        "rule_id": issue.rule_id,
                        "message": issue.message,
                    })

        return {
            "report_id": report_id,
            "fixes_applied": fixes_applied,
            "fix_count": len(fixes_applied),
            "content": fixed_content,
        }

    def _get_rules_to_check(self, rule_ids: Optional[List[str]] = None) -> List[ValidationRule]:
        if rule_ids:
            return [self._rules[rid] for rid in rule_ids if rid in self._rules]
        return list(self._rules.values())

    def get_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        for r in self._reports:
            if r.id == report_id:
                return r.to_dict()
        return None

    def list_rule_sets(self) -> List[Dict[str, Any]]:
        return [rs.to_dict() for rs in self._rule_sets.values()]

    def get_rule_set(self, ruleset_id: str) -> Optional[Dict[str, Any]]:
        rs = self._rule_sets.get(ruleset_id)
        if rs:
            return rs.to_dict()
        return None

    def get_stats(self) -> Dict[str, Any]:
        category_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        for rule in self._rules.values():
            category_counts[rule.category.value] = category_counts.get(rule.category.value, 0) + 1
            severity_counts[rule.severity.value] = severity_counts.get(rule.severity.value, 0) + 1

        total_issues = sum(len(r.issues) for r in self._reports)

        return {
            "total_rules": len(self._rules),
            "total_reports": self._report_count,
            "total_issues_found": total_issues,
            "by_category": category_counts,
            "by_severity": severity_counts,
            "ruleset_count": len(self._rule_sets),
            "autofixer_stats": self._auto_fixer.get_stats(),
        }


_global_validator_engine: Optional[ValidatorEngine] = None


def get_validator_engine() -> ValidatorEngine:
    global _global_validator_engine
    if _global_validator_engine is None:
        _global_validator_engine = ValidatorEngine()
    return _global_validator_engine
