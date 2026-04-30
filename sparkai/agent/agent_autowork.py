"""
SparkAI Agent - Autowork Loop Enforcer

Three-phase structured execution engine that enforces a strict
Plan -> Execute -> Verify cycle for agent operations. Each phase
produces structured output that must be validated before the next
phase can begin. The enforcer tracks a full transcript of all
operations and cross-checks verification claims against actual
tool calls.

Architecture:
  AutoworkEngine
    |-- PhaseStateMachine (PLAN -> EXECUTE -> VERIFY)
    |-- TranscriptTracker (full operation history)
    |-- VerificationAuditor (transcript-backed verification)
    |-- StalenessDetector (stale claim detection)
    |-- SafetyGates (consecutive failure tracking)

Phase Flow:
  1. PLAN: Agent must emit structured plan with end-state and verification gates
  2. EXECUTE: Agent performs work until completion candidate is proven
  3. VERIFY: Mandatory audit pass before clean stop

Safety Mechanisms:
  - Consecutive failure tracking with exponential backoff
  - Staleness detection (verification commands must run AFTER last code change)
  - Plan coverage checking (completion must cover every planned end-state item)
  - Abort grace period for runaway loops
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class AutoworkPhase(Enum):
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    COMPLETE = "complete"
    FAILED = "failed"


class PlanStatus(Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    PARTIAL = "partial"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class VerificationVerdict(Enum):
    PASS = "pass"
    FAIL = "fail"
    STALE = "stale"
    INCOMPLETE = "incomplete"
    PENDING = "pending"


class SafetyAction(Enum):
    CONTINUE = "continue"
    BACKOFF = "backoff"
    ABORT = "abort"
    ESCALATE = "escalate"


@dataclass
class PlanItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    verification_gate: str = ""
    completed: bool = False
    verification_result: Optional[VerificationVerdict] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "verification_gate": self.verification_gate,
            "completed": self.completed,
            "verification_result": self.verification_result.value if self.verification_result else None,
        }


@dataclass
class AutoworkPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    status_quo: str = ""
    target_end_state: str = ""
    items: List[PlanItem] = field(default_factory=list)
    verification_gates: List[str] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "status_quo": self.status_quo,
            "target_end_state": self.target_end_state,
            "items": [i.to_dict() for i in self.items],
            "verification_gates": self.verification_gates,
            "status": self.status.value,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
        }

    def all_items_completed(self) -> bool:
        return len(self.items) > 0 and all(i.completed for i in self.items)

    def coverage_ratio(self) -> float:
        if not self.items:
            return 0.0
        return sum(1 for i in self.items if i.completed) / len(self.items)


@dataclass
class TranscriptEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    phase: AutoworkPhase = AutoworkPhase.EXECUTE
    action: str = ""
    tool_name: str = ""
    tool_input: str = ""
    tool_output: str = ""
    timestamp: float = field(default_factory=time.time)
    is_code_changing: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase.value,
            "action": self.action,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "is_code_changing": self.is_code_changing,
        }


@dataclass
class VerificationClaim:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    claimed_action: str = ""
    claimed_result: str = ""
    transcript_evidence_id: Optional[str] = None
    verdict: VerificationVerdict = VerificationVerdict.PENDING
    staleness_detected: bool = False
    checked_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "claimed_action": self.claimed_action,
            "claimed_result": self.claimed_result[:200],
            "transcript_evidence_id": self.transcript_evidence_id,
            "verdict": self.verdict.value,
            "staleness_detected": self.staleness_detected,
        }


@dataclass
class SafetyState:
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3
    total_iterations: int = 0
    max_iterations: int = 90
    last_failure_time: Optional[float] = None
    abort_requested: bool = False
    grace_period_seconds: float = 30.0

    def record_failure(self) -> SafetyAction:
        self.consecutive_failures += 1
        self.total_iterations += 1
        self.last_failure_time = time.time()

        if self.consecutive_failures >= self.max_consecutive_failures:
            return SafetyAction.ABORT
        if self.consecutive_failures >= self.max_consecutive_failures - 1:
            return SafetyAction.ESCALATE
        return SafetyAction.BACKOFF

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.total_iterations += 1

    def is_exhausted(self) -> bool:
        return self.total_iterations >= self.max_iterations or self.abort_requested

    def backoff_seconds(self) -> float:
        return min(2.0 ** self.consecutive_failures, 30.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consecutive_failures": self.consecutive_failures,
            "max_consecutive_failures": self.max_consecutive_failures,
            "total_iterations": self.total_iterations,
            "max_iterations": self.max_iterations,
            "abort_requested": self.abort_requested,
        }


class TranscriptTracker:
    """
    Records all operations during an autowork session and
    provides lookup capabilities for verification auditing.
    """

    CODE_CHANGING_TOOLS = {
        "write_file", "edit_file", "create_file", "delete_file",
        "bash", "execute_tool", "act", "compose_skill", "forge_skill",
    }

    def __init__(self):
        self._entries: List[TranscriptEntry] = []
        self._last_code_change_idx: int = -1

    def record(self, phase: AutoworkPhase, action: str, tool_name: str = "", tool_input: str = "", tool_output: str = "") -> TranscriptEntry:
        is_code_changing = tool_name.lower() in self.CODE_CHANGING_TOOLS
        entry = TranscriptEntry(
            phase=phase,
            action=action,
            tool_name=tool_name,
            tool_input=tool_input[:500],
            tool_output=tool_output[:500],
            is_code_changing=is_code_changing,
        )
        self._entries.append(entry)
        if is_code_changing:
            self._last_code_change_idx = len(self._entries) - 1
        return entry

    def find_tool_calls(self, tool_name: str) -> List[TranscriptEntry]:
        return [e for e in self._entries if e.tool_name.lower() == tool_name.lower()]

    def last_code_change_time(self) -> Optional[float]:
        if self._last_code_change_idx >= 0:
            return self._entries[self._last_code_change_idx].timestamp
        return None

    def is_stale(self, claimed_timestamp: float) -> bool:
        last_change = self.last_code_change_time()
        if last_change and claimed_timestamp < last_change:
            return True
        return False

    def get_entries(self, phase: Optional[AutoworkPhase] = None) -> List[TranscriptEntry]:
        if phase:
            return [e for e in self._entries if e.phase == phase]
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self._last_code_change_idx = -1


class VerificationAuditor:
    """
    Cross-checks verification claims against the actual transcript
    to ensure that claimed verification commands were actually executed
    and that they ran after the last code-changing operation.
    """

    VERIFICATION_TOOLS = {
        "bash", "read_file", "check_health", "get_status",
        "list_agents", "validate", "test", "run_playtest",
    }

    def audit_claim(self, claim: VerificationClaim, transcript: TranscriptTracker) -> VerificationClaim:
        matching_entries = []
        for entry in transcript.get_entries(AutoworkPhase.VERIFY):
            if claim.claimed_action.lower() in entry.action.lower():
                matching_entries.append(entry)
            if claim.claimed_action.lower() in entry.tool_name.lower():
                matching_entries.append(entry)

        if not matching_entries:
            claim.verdict = VerificationVerdict.FAIL
            return claim

        latest_match = max(matching_entries, key=lambda e: e.timestamp)
        claim.transcript_evidence_id = latest_match.id

        if transcript.is_stale(latest_match.timestamp):
            claim.verdict = VerificationVerdict.STALE
            claim.staleness_detected = True
        else:
            claim.verdict = VerificationVerdict.PASS

        claim.checked_at = time.time()
        return claim

    def audit_plan_coverage(self, plan: AutoworkPlan) -> float:
        if not plan.items:
            return 0.0
        completed = sum(1 for item in plan.items if item.completed)
        return completed / len(plan.items)


class AutoworkEngine:
    """
    Three-phase structured execution engine that enforces a strict
    Plan -> Execute -> Verify cycle with transcript-backed verification.

    The engine ensures that agents cannot skip phases, that verification
    claims are cross-checked against actual tool calls, and that stale
    verification is detected and rejected.

    Usage:
        engine = AutoworkEngine()
        plan = engine.create_plan("Build a platformer game")
        engine.approve_plan(plan.id)
        result = await engine.run(plan.id, executor=my_executor)
    """

    def __init__(self, max_iterations: int = 90, max_consecutive_failures: int = 3):
        self._plans: Dict[str, AutoworkPlan] = {}
        self._transcripts: Dict[str, TranscriptTracker] = {}
        self._safety_states: Dict[str, SafetyState] = {}
        self._verification_auditor = VerificationAuditor()
        self._phase_states: Dict[str, AutoworkPhase] = {}
        self._max_iterations = max_iterations
        self._max_consecutive_failures = max_consecutive_failures
        self._completion_callbacks: List[Callable] = []
        self._session_history: List[Dict[str, Any]] = []

    def create_plan(self, goal: str, status_quo: str = "", target_end_state: str = "", items: Optional[List[Dict[str, str]]] = None) -> AutoworkPlan:
        plan = AutoworkPlan(
            goal=goal,
            status_quo=status_quo,
            target_end_state=target_end_state,
        )
        if items:
            for item_data in items:
                plan.items.append(PlanItem(
                    description=item_data.get("description", ""),
                    verification_gate=item_data.get("verification_gate", ""),
                ))
        self._plans[plan.id] = plan
        self._transcripts[plan.id] = TranscriptTracker()
        self._safety_states[plan.id] = SafetyState(
            max_iterations=self._max_iterations,
            max_consecutive_failures=self._max_consecutive_failures,
        )
        self._phase_states[plan.id] = AutoworkPhase.PLAN
        return plan

    def approve_plan(self, plan_id: str) -> bool:
        plan = self._plans.get(plan_id)
        if not plan or plan.status != PlanStatus.DRAFT:
            return False
        plan.status = PlanStatus.APPROVED
        plan.approved_at = time.time()
        self._phase_states[plan_id] = AutoworkPhase.EXECUTE
        return True

    def get_plan(self, plan_id: str) -> Optional[AutoworkPlan]:
        return self._plans.get(plan_id)

    def get_phase(self, plan_id: str) -> Optional[AutoworkPhase]:
        return self._phase_states.get(plan_id)

    def record_transcript(self, plan_id: str, phase: AutoworkPhase, action: str, tool_name: str = "", tool_input: str = "", tool_output: str = "") -> Optional[TranscriptEntry]:
        transcript = self._transcripts.get(plan_id)
        if not transcript:
            return None
        return transcript.record(phase, action, tool_name, tool_input, tool_output)

    def mark_item_completed(self, plan_id: str, item_id: str, verification_result: VerificationVerdict = VerificationVerdict.PASS) -> bool:
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        for item in plan.items:
            if item.id == item_id:
                item.completed = True
                item.verification_result = verification_result
                return True
        return False

    async def run(self, plan_id: str, executor: Optional[Callable] = None) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan or plan.status != PlanStatus.APPROVED:
            return {"status": "error", "message": "Plan not found or not approved"}

        safety = self._safety_states[plan_id]
        transcript = self._transcripts[plan_id]

        while not safety.is_exhausted():
            current_phase = self._phase_states[plan_id]

            if current_phase == AutoworkPhase.EXECUTE:
                if plan.all_items_completed():
                    self._phase_states[plan_id] = AutoworkPhase.VERIFY
                    continue

                if executor:
                    try:
                        result = await executor(plan, transcript)
                        if result:
                            safety.record_success()
                        else:
                            action = safety.record_failure()
                            if action == SafetyAction.ABORT:
                                self._phase_states[plan_id] = AutoworkPhase.FAILED
                                break
                            elif action == SafetyAction.BACKOFF:
                                await asyncio.sleep(safety.backoff_seconds())
                    except Exception:
                        action = safety.record_failure()
                        if action == SafetyAction.ABORT:
                            self._phase_states[plan_id] = AutoworkPhase.FAILED
                            break
                        await asyncio.sleep(safety.backoff_seconds())
                else:
                    safety.total_iterations += 1
                    if safety.total_iterations >= safety.max_iterations:
                        self._phase_states[plan_id] = AutoworkPhase.FAILED
                        break

            elif current_phase == AutoworkPhase.VERIFY:
                coverage = self._verification_auditor.audit_plan_coverage(plan)
                if coverage >= 1.0:
                    self._phase_states[plan_id] = AutoworkPhase.COMPLETE
                    plan.status = PlanStatus.COMPLETED
                else:
                    self._phase_states[plan_id] = AutoworkPhase.EXECUTE
                break

            else:
                break

        final_phase = self._phase_states[plan_id]
        result = {
            "plan_id": plan_id,
            "final_phase": final_phase.value,
            "coverage": plan.coverage_ratio(),
            "total_items": len(plan.items),
            "completed_items": sum(1 for i in plan.items if i.completed),
            "safety": safety.to_dict(),
            "transcript_size": len(transcript.get_entries()),
        }

        self._session_history.append(result)
        return result

    def verify_claim(self, plan_id: str, claimed_action: str, claimed_result: str = "") -> VerificationClaim:
        transcript = self._transcripts.get(plan_id)
        claim = VerificationClaim(
            claimed_action=claimed_action,
            claimed_result=claimed_result,
        )
        if transcript:
            claim = self._verification_auditor.audit_claim(claim, transcript)
        return claim

    def abort(self, plan_id: str) -> bool:
        safety = self._safety_states.get(plan_id)
        if safety:
            safety.abort_requested = True
            self._phase_states[plan_id] = AutoworkPhase.FAILED
            return True
        return False

    def list_plans(self, status: Optional[PlanStatus] = None) -> List[Dict[str, Any]]:
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return [p.to_dict() for p in plans]

    def get_transcript(self, plan_id: str, phase: Optional[AutoworkPhase] = None) -> List[Dict[str, Any]]:
        transcript = self._transcripts.get(plan_id)
        if not transcript:
            return []
        return [e.to_dict() for e in transcript.get_entries(phase)]

    def get_stats(self) -> Dict[str, Any]:
        total_plans = len(self._plans)
        by_status = {}
        for plan in self._plans.values():
            by_status[plan.status.value] = by_status.get(plan.status.value, 0) + 1

        total_sessions = len(self._session_history)
        completed_sessions = sum(1 for s in self._session_history if s.get("final_phase") == "complete")

        return {
            "total_plans": total_plans,
            "by_status": by_status,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": completed_sessions / max(total_sessions, 1),
        }


_global_autowork_engine: Optional[AutoworkEngine] = None


def get_autowork_engine() -> AutoworkEngine:
    global _global_autowork_engine
    if _global_autowork_engine is None:
        _global_autowork_engine = AutoworkEngine()
    return _global_autowork_engine
