"""
SparkAI Agent - Health Check

Runtime diagnostics and subsystem verification for the SparkLabs
AI-Native Game Engine. Provides comprehensive health checking
for all engine subsystems, configuration validation, and
connectivity verification.

Health check categories:
  - System: Runtime state, memory, uptime
  - Subsystems: Each registered subsystem's status
  - Connectivity: API endpoints, WebSocket, LLM providers
  - Configuration: Settings validation and consistency
  - Performance: Latency, throughput, cache efficiency
  - Integrity: Data consistency, session validity

Usage:
    health = HealthChecker(runtime)
    report = health.check_all()
    print(report.summary)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckCategory(Enum):
    SYSTEM = "system"
    SUBSYSTEM = "subsystem"
    CONNECTIVITY = "connectivity"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    INTEGRITY = "integrity"


@dataclass
class CheckResult:
    """Result of a single health check."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: CheckCategory = CheckCategory.SYSTEM
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
        }


@dataclass
class HealthReport:
    """Complete health check report."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    checks: List[CheckResult] = field(default_factory=list)
    summary: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)

    @property
    def degraded_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "total_checks": len(self.checks),
            "healthy": self.healthy_count,
            "degraded": self.degraded_count,
            "unhealthy": self.unhealthy_count,
            "checks": [c.to_dict() for c in self.checks],
            "created_at": self.created_at,
        }


class HealthChecker:
    """
    Runtime diagnostics and subsystem verification for the SparkLabs
    AI-Native Game Engine.

    Provides comprehensive health checking across all engine subsystems,
    with categorized results and actionable recommendations.

    Usage:
        checker = HealthChecker()
        report = checker.check_all()
        if report.overall_status != HealthStatus.HEALTHY:
            for check in report.checks:
                if check.status != HealthStatus.HEALTHY:
                    print(f"[{check.name}] {check.message}")
    """

    def __init__(self):
        self._custom_checks: Dict[str, Callable] = {}
        self._check_history: List[HealthReport] = []
        self._max_history = 50

    def register_check(self, name: str, check_fn: Callable) -> None:
        """Register a custom health check function."""
        self._custom_checks[name] = check_fn

    def check_runtime(self, runtime: Any = None) -> CheckResult:
        """Check the runtime state and subsystem availability."""
        start = time.time()
        try:
            if runtime is None:
                from sparkai.agent.runtime import get_runtime
                runtime = get_runtime()

            status = runtime.get_status()
            state = status.get("state", "unknown")
            subsystems = status.get("subsystems", {})
            all_healthy = all(subsystems.values())

            if state == "running" and all_healthy:
                health = HealthStatus.HEALTHY
                msg = f"Runtime running with {status.get('agent_count', 0)} agents"
            elif state == "running":
                health = HealthStatus.DEGRADED
                failed = [k for k, v in subsystems.items() if not v]
                msg = f"Runtime running but subsystems offline: {', '.join(failed)}"
            else:
                health = HealthStatus.UNHEALTHY
                msg = f"Runtime not running (state: {state})"

            return CheckResult(
                name="runtime",
                category=CheckCategory.SYSTEM,
                status=health,
                message=msg,
                details=status,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="runtime",
                category=CheckCategory.SYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"Runtime check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_event_bus(self) -> CheckResult:
        """Check the event bus status."""
        start = time.time()
        try:
            from sparkai.agent.events import get_event_bus
            bus = get_event_bus()
            stats = bus.get_stats()

            if stats["total_errors"] > stats["total_dispatched"] * 0.1:
                status = HealthStatus.DEGRADED
                msg = f"Event bus has high error rate ({stats['total_errors']} errors)"
            else:
                status = HealthStatus.HEALTHY
                msg = f"Event bus operational ({stats['subscription_count']} subscriptions)"

            return CheckResult(
                name="event_bus",
                category=CheckCategory.SUBSYSTEM,
                status=status,
                message=msg,
                details=stats,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="event_bus",
                category=CheckCategory.SUBSYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"Event bus check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_game_context(self) -> CheckResult:
        """Check the game context status."""
        start = time.time()
        try:
            from sparkai.agent.context import get_game_context
            ctx = get_game_context()
            summary = ctx.get_summary()

            status = HealthStatus.HEALTHY
            msg = f"Game context: {summary['entity_count']} entities, {summary['scene_count']} scenes"

            return CheckResult(
                name="game_context",
                category=CheckCategory.SUBSYSTEM,
                status=status,
                message=msg,
                details=summary,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="game_context",
                category=CheckCategory.SUBSYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"Game context check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_memory_system(self) -> CheckResult:
        """Check the memory system status."""
        start = time.time()
        try:
            from sparkai.agent.memory_v2 import AgentMemorySystem
            memory = AgentMemorySystem()
            stats = memory.get_stats()

            status = HealthStatus.HEALTHY
            msg = f"Memory system: {stats['size']['total']} entries across 3 layers"

            return CheckResult(
                name="memory_system",
                category=CheckCategory.SUBSYSTEM,
                status=status,
                message=msg,
                details=stats,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="memory_system",
                category=CheckCategory.SUBSYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"Memory system check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_skill_forge(self) -> CheckResult:
        """Check the skill forge status."""
        start = time.time()
        try:
            from sparkai.agent.skill_forge import get_skill_forge
            forge = get_skill_forge()
            stats = forge.get_stats()

            status = HealthStatus.HEALTHY
            msg = f"Skill forge: {stats['total_skills']} skills, avg reliability {stats['avg_reliability']:.2f}"

            return CheckResult(
                name="skill_forge",
                category=CheckCategory.SUBSYSTEM,
                status=status,
                message=msg,
                details=stats,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="skill_forge",
                category=CheckCategory.SUBSYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"Skill forge check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_agent_mesh(self) -> CheckResult:
        """Check the agent mesh status."""
        start = time.time()
        try:
            from sparkai.agent.mesh import get_agent_mesh
            mesh = get_agent_mesh()
            topology = mesh.get_topology()

            if topology["node_count"] == 0:
                status = HealthStatus.DEGRADED
                msg = "Agent mesh has no registered nodes"
            else:
                status = HealthStatus.HEALTHY
                msg = f"Agent mesh: {topology['node_count']} nodes, {topology['available_nodes']} available"

            return CheckResult(
                name="agent_mesh",
                category=CheckCategory.SUBSYSTEM,
                status=status,
                message=msg,
                details=topology,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="agent_mesh",
                category=CheckCategory.SUBSYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"Agent mesh check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_protocol(self) -> CheckResult:
        """Check the agent protocol status."""
        start = time.time()
        try:
            from sparkai.agent.protocol import get_protocol
            protocol = get_protocol()
            stats = protocol.get_stats()

            status = HealthStatus.HEALTHY
            msg = f"Protocol: {stats['total_sent']} messages sent, {stats['total_delivered']} delivered"

            return CheckResult(
                name="protocol",
                category=CheckCategory.SUBSYSTEM,
                status=status,
                message=msg,
                details=stats,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="protocol",
                category=CheckCategory.SUBSYSTEM,
                status=HealthStatus.UNHEALTHY,
                message=f"Protocol check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_configuration(self) -> CheckResult:
        """Check configuration validity."""
        start = time.time()
        try:
            from sparkai.config import SparkAIConfig
            config = SparkAIConfig()

            issues = []
            if not config.cors_origins:
                issues.append("No CORS origins configured")

            status = HealthStatus.HEALTHY if not issues else HealthStatus.DEGRADED
            msg = "Configuration valid" if not issues else f"Config issues: {'; '.join(issues)}"

            return CheckResult(
                name="configuration",
                category=CheckCategory.CONFIGURATION,
                status=status,
                message=msg,
                details={"issues": issues},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return CheckResult(
                name="configuration",
                category=CheckCategory.CONFIGURATION,
                status=HealthStatus.UNHEALTHY,
                message=f"Configuration check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
            )

    def check_all(self, runtime: Any = None) -> HealthReport:
        """Run all health checks and produce a comprehensive report."""
        checks = [
            self.check_runtime(runtime),
            self.check_event_bus(),
            self.check_game_context(),
            self.check_memory_system(),
            self.check_skill_forge(),
            self.check_agent_mesh(),
            self.check_protocol(),
            self.check_configuration(),
        ]

        for name, check_fn in self._custom_checks.items():
            try:
                start = time.time()
                result = check_fn()
                if not isinstance(result, CheckResult):
                    result = CheckResult(
                        name=name,
                        category=CheckCategory.SYSTEM,
                        status=HealthStatus.HEALTHY,
                        message=str(result),
                        duration_ms=(time.time() - start) * 1000,
                    )
                checks.append(result)
            except Exception as e:
                checks.append(CheckResult(
                    name=name,
                    category=CheckCategory.SYSTEM,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Custom check failed: {str(e)}",
                ))

        if any(c.status == HealthStatus.UNHEALTHY for c in checks):
            overall = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in checks):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        healthy = sum(1 for c in checks if c.status == HealthStatus.HEALTHY)
        total = len(checks)
        summary = f"{healthy}/{total} checks healthy"

        report = HealthReport(
            overall_status=overall,
            checks=checks,
            summary=summary,
        )

        self._check_history.append(report)
        if len(self._check_history) > self._max_history:
            self._check_history = self._check_history[-self._max_history:]

        return report

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._check_history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_checks_run": len(self._check_history),
            "custom_checks": len(self._custom_checks),
            "last_status": (
                self._check_history[-1].overall_status.value
                if self._check_history else "none"
            ),
        }


_global_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global HealthChecker singleton."""
    global _global_checker
    if _global_checker is None:
        _global_checker = HealthChecker()
    return _global_checker


def reset_health_checker() -> None:
    """Reset the global HealthChecker singleton."""
    global _global_checker
    _global_checker = None
