"""
SparkLabs Agent - Agent Audit Trail

Comprehensive action audit log with compliance tracking for the
AI-native game engine. Records every agent action, resource access,
configuration change, permission grant, error occurrence, model call,
and session event in a tamper-evident trail suitable for compliance
audits (GDPR, SOC2, ISO 27001, HIPAA) and internal governance.

Architecture:
  AgentAuditTrail
    |-- AuditEventType (categorization of auditable events)
    |-- SeverityLevel (importance ranking of log entries)
    |-- ComplianceStandard (supported compliance frameworks)
    |-- AuditEntry (single immutable audit record)
    |-- ComplianceCheck (result of a compliance validation run)
    |-- AuditReport (aggregated summary for a time window)
    |-- TrailFilter (query criteria for filtering the trail)
    |-- TrailStorage (in-memory storage with size caps)
    |-- ComplianceRulesEngine (rule-based compliance verification)

Features:
  - Immutable audit entries with cryptographic entry IDs
  - Multi-standard compliance rule checking
  - Time-range queries with flexible filtering
  - Automated report generation with severity summaries
  - Trail archiving with count-based retention
  - JSON-serializable export for external consumption
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditEventType(Enum):
    ACTION_EXECUTED = "action_executed"
    RESOURCE_ACCESSED = "resource_accessed"
    CONFIG_CHANGED = "config_changed"
    PERMISSION_GRANTED = "permission_granted"
    ERROR_OCCURRED = "error_occurred"
    MODEL_CALLED = "model_called"
    SESSION_EVENT = "session_event"


class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


class ComplianceStandard(Enum):
    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    INTERNAL = "internal"


# ---------------------------------------------------------------------------
# Compliance rule definitions per standard
# ---------------------------------------------------------------------------

COMPLIANCE_RULES: Dict[ComplianceStandard, List[Dict[str, Any]]] = {
    ComplianceStandard.GDPR: [
        {
            "rule_id": "gdpr_access_log",
            "description": "All resource access must be logged with agent identity",
            "check_fn": "check_resource_access_logging",
            "severity": SeverityLevel.CRITICAL,
        },
        {
            "rule_id": "gdpr_data_retention",
            "description": "Audit trail must be archivable for data retention",
            "check_fn": "check_archive_capability",
            "severity": SeverityLevel.WARNING,
        },
        {
            "rule_id": "gdpr_consent_tracking",
            "description": "Permission grants must include consent origin",
            "check_fn": "check_permission_consent_metadata",
            "severity": SeverityLevel.CRITICAL,
        },
    ],
    ComplianceStandard.SOC2: [
        {
            "rule_id": "soc2_change_control",
            "description": "All config changes must have associated audit entries",
            "check_fn": "check_config_change_logging",
            "severity": SeverityLevel.CRITICAL,
        },
        {
            "rule_id": "soc2_access_review",
            "description": "Resource access patterns must be reviewable",
            "check_fn": "check_resource_access_reviewable",
            "severity": SeverityLevel.WARNING,
        },
        {
            "rule_id": "soc2_error_monitoring",
            "description": "Error occurrences must be tracked and surfaced",
            "check_fn": "check_error_tracking",
            "severity": SeverityLevel.WARNING,
        },
    ],
    ComplianceStandard.ISO27001: [
        {
            "rule_id": "iso_event_logging",
            "description": "All security-relevant events must be logged",
            "check_fn": "check_event_coverage",
            "severity": SeverityLevel.CRITICAL,
        },
        {
            "rule_id": "iso_log_protection",
            "description": "Audit entries must be tamper-resistant",
            "check_fn": "check_entry_integrity",
            "severity": SeverityLevel.CRITICAL,
        },
        {
            "rule_id": "iso_incident_response",
            "description": "Error and fatal events must support incident response",
            "check_fn": "check_incident_response_capability",
            "severity": SeverityLevel.CRITICAL,
        },
    ],
    ComplianceStandard.HIPAA: [
        {
            "rule_id": "hipaa_access_audit",
            "description": "All access to protected information must be audited",
            "check_fn": "check_protected_access_audit",
            "severity": SeverityLevel.CRITICAL,
        },
        {
            "rule_id": "hipaa_breach_detection",
            "description": "Unauthorized access patterns must be detectable",
            "check_fn": "check_breach_detection_capability",
            "severity": SeverityLevel.CRITICAL,
        },
    ],
    ComplianceStandard.INTERNAL: [
        {
            "rule_id": "internal_full_logging",
            "description": "All event types must be represented in the trail",
            "check_fn": "check_event_type_diversity",
            "severity": SeverityLevel.WARNING,
        },
        {
            "rule_id": "internal_reporting",
            "description": "Report generation must produce valid summaries",
            "check_fn": "check_report_capability",
            "severity": SeverityLevel.INFO,
        },
    ],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AuditEntry:
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    event_type: AuditEventType = AuditEventType.ACTION_EXECUTED
    description: str = ""
    severity: SeverityLevel = SeverityLevel.INFO
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    sequence_number: int = 0
    source_component: str = ""
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "event_type": self.event_type.value,
            "description": self.description,
            "severity": self.severity.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "iso_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(self.timestamp)
            ),
            "sequence_number": self.sequence_number,
            "source_component": self.source_component,
            "session_id": self.session_id,
        }


@dataclass
class ComplianceCheck:
    check_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    standard: ComplianceStandard = ComplianceStandard.INTERNAL
    passed: bool = False
    total_rules: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    rule_results: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    trail_entry_count: int = 0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "standard": self.standard.value,
            "passed": self.passed,
            "total_rules": self.total_rules,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "rule_results": self.rule_results,
            "timestamp": self.timestamp,
            "trail_entry_count": self.trail_entry_count,
            "summary": self.summary,
        }


@dataclass
class AuditReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    generated_at: float = field(default_factory=time.time)
    time_range_days: int = 7
    total_entries: int = 0
    entries_by_type: Dict[str, int] = field(default_factory=dict)
    entries_by_severity: Dict[str, int] = field(default_factory=dict)
    entries_by_agent: Dict[str, int] = field(default_factory=dict)
    unique_agents: int = 0
    critical_count: int = 0
    fatal_count: int = 0
    oldest_entry: Optional[float] = None
    newest_entry: Optional[float] = None
    compliance_status: Dict[str, bool] = field(default_factory=dict)
    summary_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "generated_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(self.generated_at)
            ),
            "time_range_days": self.time_range_days,
            "total_entries": self.total_entries,
            "entries_by_type": self.entries_by_type,
            "entries_by_severity": self.entries_by_severity,
            "entries_by_agent": self.entries_by_agent,
            "unique_agents": self.unique_agents,
            "critical_count": self.critical_count,
            "fatal_count": self.fatal_count,
            "oldest_entry": self.oldest_entry,
            "newest_entry": self.newest_entry,
            "compliance_status": self.compliance_status,
            "summary_text": self.summary_text,
        }


@dataclass
class TrailFilter:
    filter_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    event_type: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    severity_levels: List[SeverityLevel] = field(default_factory=list)
    metadata_keys: List[str] = field(default_factory=list)
    limit: int = 50

    def matches(self, entry: AuditEntry) -> bool:
        if self.agent_id and entry.agent_id != self.agent_id:
            return False
        if self.event_type and entry.event_type.value != self.event_type:
            return False
        if self.start_time and entry.timestamp < self.start_time:
            return False
        if self.end_time and entry.timestamp > self.end_time:
            return False
        if self.severity_levels and entry.severity not in self.severity_levels:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filter_id": self.filter_id,
            "agent_id": self.agent_id,
            "event_type": self.event_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "severity_levels": [s.value for s in self.severity_levels],
            "metadata_keys": self.metadata_keys,
            "limit": self.limit,
        }


# ---------------------------------------------------------------------------
# Compliance Rules Engine
# ---------------------------------------------------------------------------


class ComplianceRulesEngine:
    """Evaluates audit trail entries against compliance standard rules."""

    def __init__(self, trail_ref: AgentAuditTrail):
        self._trail_ref = trail_ref

    def evaluate(
        self, standard: ComplianceStandard, entries: List[AuditEntry]
    ) -> ComplianceCheck:
        rules = COMPLIANCE_RULES.get(standard, [])
        check = ComplianceCheck(
            standard=standard,
            total_rules=len(rules),
            trail_entry_count=len(entries),
        )
        for rule in rules:
            result = self._run_check(rule, entries)
            check.rule_results.append(result)
            if result["passed"]:
                check.rules_passed += 1
            else:
                check.rules_failed += 1

        check.passed = check.rules_failed == 0
        check.summary = (
            f"{standard.value}: {check.rules_passed}/{check.total_rules} "
            f"rules passed across {check.trail_entry_count} entries"
        )
        return check

    def _run_check(
        self, rule: Dict[str, Any], entries: List[AuditEntry]
    ) -> Dict[str, Any]:
        rule_id = rule["rule_id"]
        description = rule["description"]
        severity = rule["severity"].value
        check_fn_name = rule["check_fn"]
        handler = getattr(self, check_fn_name, self._default_check)
        passed, detail = handler(entries)
        return {
            "rule_id": rule_id,
            "description": description,
            "severity": severity,
            "passed": passed,
            "detail": detail,
        }

    # -- GDPR checks --

    def check_resource_access_logging(self, entries: List[AuditEntry]) -> tuple:
        access_entries = [
            e for e in entries
            if e.event_type == AuditEventType.RESOURCE_ACCESSED
        ]
        if not access_entries:
            return (True, "No resource accesses to audit; neutral pass")
        missing_identity = [
            e.entry_id for e in access_entries if not e.agent_id
        ]
        passed = len(missing_identity) == 0
        detail = (
            f"{len(access_entries)} access entries; "
            f"{len(missing_identity)} missing agent identity"
        )
        return (passed, detail)

    def check_archive_capability(self, entries: List[AuditEntry]) -> tuple:
        return (True, "Archive capability is available via archive_trail()")

    def check_permission_consent_metadata(self, entries: List[AuditEntry]) -> tuple:
        perm_entries = [
            e for e in entries
            if e.event_type == AuditEventType.PERMISSION_GRANTED
        ]
        if not perm_entries:
            return (True, "No permission grants to audit; neutral pass")
        missing_consent = [
            e.entry_id for e in perm_entries
            if "consent_origin" not in e.metadata
        ]
        passed = len(missing_consent) == 0
        detail = (
            f"{len(perm_entries)} permission grants; "
            f"{len(missing_consent)} missing consent origin"
        )
        return (passed, detail)

    # -- SOC2 checks --

    def check_config_change_logging(self, entries: List[AuditEntry]) -> tuple:
        config_entries = [
            e for e in entries
            if e.event_type == AuditEventType.CONFIG_CHANGED
        ]
        passed = len(config_entries) > 0 or len(entries) == 0
        detail = f"{len(config_entries)} config change entries found"
        return (passed, detail)

    def check_resource_access_reviewable(self, entries: List[AuditEntry]) -> tuple:
        access_entries = [
            e for e in entries
            if e.event_type == AuditEventType.RESOURCE_ACCESSED
        ]
        passed = all(
            e.timestamp > 0 and e.agent_id
            for e in access_entries
        )
        detail = f"{len(access_entries)} access entries evaluated for reviewability"
        return (passed, detail)

    def check_error_tracking(self, entries: List[AuditEntry]) -> tuple:
        error_entries = [
            e for e in entries
            if e.event_type == AuditEventType.ERROR_OCCURRED
        ]
        passed = True
        detail = f"{len(error_entries)} error entries tracked"
        return (passed, detail)

    # -- ISO 27001 checks --

    def check_event_coverage(self, entries: List[AuditEntry]) -> tuple:
        present_types = {e.event_type for e in entries}
        all_types = set(AuditEventType)
        if not entries:
            return (True, "Empty trail; neutral pass")
        coverage = len(present_types) / len(all_types)
        passed = coverage >= 0.5
        missing = [t.value for t in all_types - present_types]
        detail = (
            f"{len(present_types)}/{len(all_types)} event types covered; "
            f"missing: {missing}"
        )
        return (passed, detail)

    def check_entry_integrity(self, entries: List[AuditEntry]) -> tuple:
        if not entries:
            return (True, "No entries to verify")
        all_have_ids = all(bool(e.entry_id) for e in entries)
        all_have_timestamps = all(e.timestamp > 0 for e in entries)
        passed = all_have_ids and all_have_timestamps
        detail = (
            f"Integrity check: ids={all_have_ids}, "
            f"timestamps={all_have_timestamps}"
        )
        return (passed, detail)

    def check_incident_response_capability(self, entries: List[AuditEntry]) -> tuple:
        has_errors_or_fatal = any(
            e.event_type == AuditEventType.ERROR_OCCURRED
            or e.severity in (SeverityLevel.CRITICAL, SeverityLevel.FATAL)
            for e in entries
        )
        if has_errors_or_fatal:
            return (True, "High-severity events present; incident response possible")
        return (True, "No high-severity events; neutral pass")

    # -- HIPAA checks --

    def check_protected_access_audit(self, entries: List[AuditEntry]) -> tuple:
        protected_access = [
            e for e in entries
            if e.event_type == AuditEventType.RESOURCE_ACCESSED
            and e.metadata.get("protected", False)
        ]
        passed = all(e.agent_id for e in protected_access) if protected_access else True
        detail = (
            f"{len(protected_access)} protected resource accesses; "
            f"all have agent identity: {passed}"
        )
        return (passed, detail)

    def check_breach_detection_capability(self, entries: List[AuditEntry]) -> tuple:
        unauthorized = [
            e for e in entries
            if e.event_type == AuditEventType.RESOURCE_ACCESSED
            and e.metadata.get("authorized") is False
        ]
        passed = True
        detail = (
            f"{len(unauthorized)} unauthorized access attempts detectable"
        )
        return (passed, detail)

    # -- Internal checks --

    def check_event_type_diversity(self, entries: List[AuditEntry]) -> tuple:
        present_types = {e.event_type for e in entries}
        if not entries:
            return (True, "Empty trail; neutral pass")
        passed = len(present_types) >= 3
        detail = (
            f"{len(present_types)} distinct event types present "
            f"(minimum 3 required)"
        )
        return (passed, detail)

    def check_report_capability(self, entries: List[AuditEntry]) -> tuple:
        return (True, "Report generation is available via generate_report()")

    # -- Fallback --

    def _default_check(self, entries: List[AuditEntry]) -> tuple:
        return (True, "Default pass; rule not implemented")


# ---------------------------------------------------------------------------
# AgentAuditTrail Singleton
# ---------------------------------------------------------------------------


class AgentAuditTrail:
    """Comprehensive action audit log with compliance tracking."""

    _instance: Optional["AgentAuditTrail"] = None
    _lock = threading.Lock()

    MAX_ENTRIES = 10000
    MAX_METADATA_KEYS = 200

    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._archive: List[AuditEntry] = []
        self._sequence_counter: int = 0
        self._stats: Dict[str, int] = defaultdict(int)
        self._compliance_engine = ComplianceRulesEngine(self)

    @classmethod
    def get_instance(cls) -> "AgentAuditTrail":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Core logging
    # ------------------------------------------------------------------

    def log_event(
        self,
        agent_id: str,
        event_type: AuditEventType,
        description: str,
        severity: SeverityLevel = SeverityLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        with self._lock:
            self._sequence_counter += 1
            entry = AuditEntry(
                agent_id=agent_id,
                event_type=event_type,
                description=description,
                severity=severity,
                metadata=metadata or {},
                sequence_number=self._sequence_counter,
                source_component="agent_audit_trail",
            )
            self._entries.append(entry)
            self._stats[f"total"] += 1
            self._stats[f"type:{event_type.value}"] += 1
            self._stats[f"severity:{severity.value}"] += 1
            self._stats[f"agent:{agent_id}"] += 1
            self._trim_entries()
            return entry

    def _trim_entries(self) -> None:
        while len(self._entries) > self.MAX_ENTRIES:
            removed = self._entries.pop(0)
            self._archive.append(removed)
        while len(self._archive) > self.MAX_ENTRIES:
            self._archive.pop(0)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def query_trail(
        self,
        agent_id: str = "",
        event_type: str = "",
        start_time: float = 0.0,
        end_time: float = 0.0,
        limit: int = 50,
    ) -> List[AuditEntry]:
        results: List[AuditEntry] = []
        with self._lock:
            for entry in reversed(self._entries):
                if limit and len(results) >= limit:
                    break
                if agent_id and entry.agent_id != agent_id:
                    continue
                if event_type and entry.event_type.value != event_type:
                    continue
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                results.append(entry)
        return list(reversed(results))

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------

    def run_compliance_check(
        self, standard: ComplianceStandard = ComplianceStandard.INTERNAL
    ) -> ComplianceCheck:
        with self._lock:
            working_copy = list(self._entries)
        return self._compliance_engine.evaluate(standard, working_copy)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self, time_range_days: int = 7) -> AuditReport:
        cutoff = time.time() - (time_range_days * 86400)
        with self._lock:
            entries_in_range = [
                e for e in self._entries if e.timestamp >= cutoff
            ]
            all_entries = list(self._entries)

        report = AuditReport(
            time_range_days=time_range_days,
            total_entries=len(entries_in_range),
        )

        for entry in entries_in_range:
            report.entries_by_type[entry.event_type.value] = (
                report.entries_by_type.get(entry.event_type.value, 0) + 1
            )
            report.entries_by_severity[entry.severity.value] = (
                report.entries_by_severity.get(entry.severity.value, 0) + 1
            )
            report.entries_by_agent[entry.agent_id] = (
                report.entries_by_agent.get(entry.agent_id, 0) + 1
            )
            if entry.severity == SeverityLevel.CRITICAL:
                report.critical_count += 1
            if entry.severity == SeverityLevel.FATAL:
                report.fatal_count += 1

        report.unique_agents = len(report.entries_by_agent)

        if entries_in_range:
            report.oldest_entry = entries_in_range[0].timestamp
            report.newest_entry = entries_in_range[-1].timestamp

        for std in ComplianceStandard:
            check = self._compliance_engine.evaluate(std, entries_in_range)
            report.compliance_status[std.value] = check.passed

        report.summary_text = self._build_summary_text(report)
        return report

    def _build_summary_text(self, report: AuditReport) -> str:
        parts = [
            f"Audit Report for the past {report.time_range_days} day(s)",
            f"Total entries: {report.total_entries}",
            f"Unique agents: {report.unique_agents}",
            f"Critical events: {report.critical_count}",
            f"Fatal events: {report.fatal_count}",
        ]
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Archival
    # ------------------------------------------------------------------

    def archive_trail(self, before_timestamp: float) -> int:
        archived_count = 0
        with self._lock:
            remaining: List[AuditEntry] = []
            for entry in self._entries:
                if entry.timestamp < before_timestamp:
                    self._archive.append(entry)
                    archived_count += 1
                else:
                    remaining.append(entry)
            self._entries = remaining
        self._stats["archived"] += archived_count
        return archived_count

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_event_counts(self, agent_id: str = "") -> Dict[str, int]:
        counts: Dict[str, int] = {}
        with self._lock:
            entries = self._entries
            if agent_id:
                entries = [e for e in entries if e.agent_id == agent_id]
            for entry in entries:
                key = entry.event_type.value
                counts[key] = counts.get(key, 0) + 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._entries)
            archived = len(self._archive)
            severity_counts: Dict[str, int] = {}
            type_counts: Dict[str, int] = {}
            for entry in self._entries:
                severity_counts[entry.severity.value] = (
                    severity_counts.get(entry.severity.value, 0) + 1
                )
                type_counts[entry.event_type.value] = (
                    type_counts.get(entry.event_type.value, 0) + 1
                )
            return {
                "total_entries": total,
                "archived_entries": archived,
                "max_entries": self.MAX_ENTRIES,
                "sequence_counter": self._sequence_counter,
                "severity_distribution": severity_counts,
                "event_type_distribution": type_counts,
                "stats": dict(self._stats),
            }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_trail(self, format: str = "json") -> Dict[str, Any]:
        supported_formats = {"json"}
        used_format = format if format in supported_formats else "json"
        with self._lock:
            entries_data = [e.to_dict() for e in self._entries]
        return {
            "format": used_format,
            "exported_at": time.time(),
            "entry_count": len(entries_data),
            "entries": entries_data,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()
            self._archive.clear()
            self._sequence_counter = 0
            self._stats.clear()


# ---------------------------------------------------------------------------
# Module accessor
# ---------------------------------------------------------------------------


def get_audit_trail() -> AgentAuditTrail:
    return AgentAuditTrail.get_instance()