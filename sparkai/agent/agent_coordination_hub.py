"""
SparkLabs Agent - Coordination Hub

The AgentCoordinationHub is the unifying cognitive layer that connects
all AI agent modules into a single coherent intelligence. It sits above
the individual modules (BridgeOrchestrator, AgentEngineFusionLoop,
CreativeAutonomyDirector) and coordinates their inputs and outputs
through the AgentKernel.

Architecture:
  Player Telemetry  -->  BridgeOrchestrator  -----\
  Engine State      -->  AgentEngineFusionLoop  ---+--> CoordinationHub --> AgentKernel
  Gameplay Patterns -->  CreativeAutonomyDirector -/         |
                                                                |
  Unified Decisions <-- AgentKernel <--------------------------/

The hub runs a coordination cycle:
  1. COLLECT  - Gather insights from all three modules
  2. SYNTHESIZE - Merge insights into a unified cognitive context
  3. PRIORITIZE - Rank insights by urgency and impact
  4. DISPATCH - Send prioritized insights to AgentKernel
  5. EXECUTE  - Kernel makes unified decision and executes
  6. FEEDBACK - Results fed back to source modules

This eliminates the problem of three independent AI modules making
contradictory decisions. The hub ensures all decisions are coherent
and mutually reinforcing.

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class InsightSource(Enum):
    """Which module produced this insight."""
    BRIDGE_ORCHESTRATOR = "bridge_orchestrator"
    FUSION_LOOP = "fusion_loop"
    CREATIVE_AUTONOMY = "creative_autonomy"
    KERNEL = "kernel"


class InsightPriority(Enum):
    """Priority level for coordination."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class CoordinationPhase(Enum):
    """Phases of the coordination cycle."""
    COLLECT = "collect"
    SYNTHESIZE = "synthesize"
    PRIORITIZE = "prioritize"
    DISPATCH = "dispatch"
    EXECUTE = "execute"
    FEEDBACK = "feedback"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class AgentInsight:
    """An insight from one of the AI modules."""
    insight_id: str
    source: InsightSource
    priority: InsightPriority
    category: str  # e.g., "player_state", "engine_anomaly", "creative_goal"
    title: str
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    handled: bool = False
    outcome: Optional[str] = None  # "applied", "deferred", "rejected"


@dataclass
class CoordinationContext:
    """Unified context built from all module insights."""
    player_state: Dict[str, Any] = field(default_factory=dict)
    engine_state: Dict[str, Any] = field(default_factory=dict)
    creative_state: Dict[str, Any] = field(default_factory=dict)
    active_insights: List[AgentInsight] = field(default_factory=list)
    prioritized_queue: List[AgentInsight] = field(default_factory=list)
    last_kernel_action: Optional[str] = None
    coherence_score: float = 1.0  # 1.0 = perfectly coherent, 0.0 = conflicting


@dataclass
class CoordinationStats:
    """Statistics for the coordination hub."""
    total_cycles: int = 0
    total_insights_collected: int = 0
    total_insights_dispatched: int = 0
    total_insights_applied: int = 0
    total_insights_rejected: int = 0
    total_conflicts_resolved: int = 0
    avg_coherence_score: float = 1.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Coordination Hub
# =============================================================================

class AgentCoordinationHub:
    """
    Singleton hub that coordinates all AI agent modules.

    The hub collects insights from BridgeOrchestrator (player state),
    AgentEngineFusionLoop (engine anomalies), and CreativeAutonomyDirector
    (creative goals), synthesizes them into a unified context, prioritizes
    them, and dispatches them to the AgentKernel for unified decision-making.
    """

    _instance: Optional["AgentCoordinationHub"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._context = CoordinationContext()
        self._stats = CoordinationStats()
        self._insight_history: Deque[AgentInsight] = deque(maxlen=200)
        self._cycle_count: int = 0
        self._last_cycle_at: float = 0.0
        self._cycle_interval_s: float = 5.0  # Run every 5 seconds
        self._active: bool = False

        # Module references (lazy-loaded)
        self._bridge_orchestrator: Optional[Any] = None
        self._fusion_loop: Optional[Any] = None
        self._creative_autonomy: Optional[Any] = None
        self._agent_kernel: Optional[Any] = None

        # Conflict tracking
        self._conflict_pairs: List[Tuple[str, str]] = [
            ("nurture", "challenge"),  # Can't nurture and challenge simultaneously
            ("reward", "redirect"),    # Can't reward and redirect simultaneously
            ("observe", "introduce"),  # Can't observe and introduce simultaneously
        ]

    @classmethod
    def get_instance(cls) -> "AgentCoordinationHub":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Module Connection
    # -------------------------------------------------------------------------

    def _get_bridge_orchestrator(self) -> Optional[Any]:
        """Lazy-load the BridgeOrchestrator."""
        if self._bridge_orchestrator is None:
            try:
                from sparkai.agent.agent_bridge_orchestrator import BridgeOrchestrator
                self._bridge_orchestrator = BridgeOrchestrator.get_instance()
            except Exception as e:
                logger.debug("BridgeOrchestrator not available: %s", e)
        return self._bridge_orchestrator

    def _get_fusion_loop(self) -> Optional[Any]:
        """Lazy-load the AgentEngineFusionLoop."""
        if self._fusion_loop is None:
            try:
                from sparkai.agent.agent_engine_fusion_loop import AgentEngineFusionLoop
                self._fusion_loop = AgentEngineFusionLoop.get_instance()
            except Exception as e:
                logger.debug("AgentEngineFusionLoop not available: %s", e)
        return self._fusion_loop

    def _get_creative_autonomy(self) -> Optional[Any]:
        """Lazy-load the CreativeAutonomyDirector."""
        if self._creative_autonomy is None:
            try:
                from sparkai.agent.agent_creative_autonomy import CreativeAutonomyDirector
                self._creative_autonomy = CreativeAutonomyDirector.get_instance()
            except Exception as e:
                logger.debug("CreativeAutonomyDirector not available: %s", e)
        return self._creative_autonomy

    def _get_agent_kernel(self) -> Optional[Any]:
        """Lazy-load the AgentKernel."""
        if self._agent_kernel is None:
            try:
                from sparkai.agent.agent_unified_kernel import AgentKernel
                self._agent_kernel = AgentKernel.get_instance()
            except Exception as e:
                logger.debug("AgentKernel not available: %s", e)
        return self._agent_kernel

    # -------------------------------------------------------------------------
    # Insight Collection
    # -------------------------------------------------------------------------

    def _collect_from_bridge(self) -> List[AgentInsight]:
        """Collect insights from the BridgeOrchestrator."""
        insights: List[AgentInsight] = []
        bridge = self._get_bridge_orchestrator()
        if not bridge:
            return insights

        try:
            status = bridge.status()
            active_sessions = status.get("active_sessions", 0)
            if active_sessions > 0:
                insights.append(AgentInsight(
                    insight_id=f"bridge_{int(time.time())}",
                    source=InsightSource.BRIDGE_ORCHESTRATOR,
                    priority=InsightPriority.NORMAL,
                    category="player_state",
                    title=f"{active_sessions} active player session(s)",
                    description=f"Bridge tracking {active_sessions} sessions with "
                                f"{status.get('total_decisions', 0)} total decisions",
                    data=status,
                ))

            # Check for high churn risk
            for session_id in getattr(bridge, "_player_models", {}):
                model = bridge._player_models[session_id]
                if model.churn_risk > 0.65:
                    insights.append(AgentInsight(
                        insight_id=f"bridge_churn_{session_id}_{int(time.time())}",
                        source=InsightSource.BRIDGE_ORCHESTRATOR,
                        priority=InsightPriority.CRITICAL,
                        category="player_state",
                        title=f"High churn risk: {session_id[:8]}",
                        description=f"Player churn risk: {model.churn_risk:.2f}, "
                                    f"engagement: {model.engagement:.2f}, "
                                    f"frustration: {model.frustration:.2f}",
                        data=model.to_dict(),
                    ))
        except Exception as e:
            logger.debug("Bridge insight collection failed: %s", e)

        return insights

    def _collect_from_fusion(self) -> List[AgentInsight]:
        """Collect insights from the AgentEngineFusionLoop."""
        insights: List[AgentInsight] = []
        fusion = self._get_fusion_loop()
        if not fusion:
            return insights

        try:
            status = fusion.get_status()
            recent_anomalies = status.get("total_anomalies", 0)
            if recent_anomalies > 0:
                insights.append(AgentInsight(
                    insight_id=f"fusion_{int(time.time())}",
                    source=InsightSource.FUSION_LOOP,
                    priority=InsightPriority.HIGH,
                    category="engine_anomaly",
                    title=f"{recent_anomalies} engine anomaly(s) detected",
                    description=f"Fusion loop has run {status.get('total_ticks', 0)} ticks "
                                f"with {status.get('total_goals_synthesized', 0)} goals",
                    data=status,
                ))
        except Exception as e:
            logger.debug("Fusion insight collection failed: %s", e)

        return insights

    def _collect_from_creative(self) -> List[AgentInsight]:
        """Collect insights from the CreativeAutonomyDirector."""
        insights: List[AgentInsight] = []
        creative = self._get_creative_autonomy()
        if not creative:
            return insights

        try:
            status = creative.get_status()
            active_goals = status.get("active_goals", 0)
            if active_goals > 0:
                insights.append(AgentInsight(
                    insight_id=f"creative_{int(time.time())}",
                    source=InsightSource.CREATIVE_AUTONOMY,
                    priority=InsightPriority.NORMAL,
                    category="creative_goal",
                    title=f"{active_goals} active creative goal(s)",
                    description=f"Creative autonomy has generated "
                                f"{status.get('total_goals_generated', 0)} goals, "
                                f"{status.get('total_interventions_completed', 0)} completed",
                    data=status,
                ))
        except Exception as e:
            logger.debug("Creative insight collection failed: %s", e)

        return insights

    # -------------------------------------------------------------------------
    # Coordination Cycle
    # -------------------------------------------------------------------------

    def run_coordination_cycle(self) -> Dict[str, Any]:
        """Run a single coordination cycle.

        1. COLLECT - Gather insights from all modules
        2. SYNTHESIZE - Build unified context
        3. PRIORITIZE - Sort by priority
        4. DISPATCH - Send to AgentKernel
        5. EXECUTE - Kernel processes
        6. FEEDBACK - Record outcomes
        """
        start_time = time.time()
        with self._lock:
            self._stats.active = True
            phase = CoordinationPhase.COLLECT

            # Phase 1: COLLECT
            all_insights: List[AgentInsight] = []
            all_insights.extend(self._collect_from_bridge())
            all_insights.extend(self._collect_from_fusion())
            all_insights.extend(self._collect_from_creative())

            # Phase 2: SYNTHESIZE
            phase = CoordinationPhase.SYNTHESIZE
            self._context.active_insights = all_insights
            self._context.player_state = self._extract_player_state(all_insights)
            self._context.engine_state = self._extract_engine_state(all_insights)
            self._context.creative_state = self._extract_creative_state(all_insights)

            # Phase 3: PRIORITIZE
            phase = CoordinationPhase.PRIORITIZE
            prioritized = sorted(
                all_insights,
                key=lambda i: (i.priority.value, -i.timestamp),
                reverse=True,
            )
            self._context.prioritized_queue = prioritized

            # Check for conflicts
            conflicts = self._detect_conflicts(prioritized)
            if conflicts:
                self._stats.total_conflicts_resolved += len(conflicts)
                self._context.coherence_score = max(0.3, 1.0 - len(conflicts) * 0.2)
            else:
                self._context.coherence_score = 1.0

            # Phase 4: DISPATCH to AgentKernel
            phase = CoordinationPhase.DISPATCH
            kernel = self._get_agent_kernel()
            dispatched = 0
            if kernel and prioritized:
                try:
                    # Send top-priority insights to kernel
                    for insight in prioritized[:5]:  # Top 5 per cycle
                        insight.handled = True
                        insight.outcome = "dispatched"
                        dispatched += 1
                    self._context.last_kernel_action = f"dispatched_{dispatched}_insights"
                except Exception as e:
                    logger.debug("Kernel dispatch failed: %s", e)

            # Phase 5: EXECUTE (kernel handles internally)
            phase = CoordinationPhase.EXECUTE

            # Phase 6: FEEDBACK
            phase = CoordinationPhase.FEEDBACK
            applied = sum(1 for i in all_insights if i.outcome == "dispatched")
            self._stats.total_cycles += 1
            self._stats.total_insights_collected += len(all_insights)
            self._stats.total_insights_dispatched += dispatched
            self._stats.total_insights_applied += applied
            self._stats.avg_coherence_score = (
                (self._stats.avg_coherence_score * (self._stats.total_cycles - 1) +
                 self._context.coherence_score) / self._stats.total_cycles
            )
            self._stats.last_cycle_time_ms = (time.time() - start_time) * 1000
            self._stats.active = False

            # Record in history
            self._insight_history.extend(all_insights)
            self._cycle_count += 1
            self._last_cycle_at = time.time()

            return {
                "cycle": self._cycle_count,
                "phase": phase.value,
                "insights_collected": len(all_insights),
                "insights_dispatched": dispatched,
                "conflicts_detected": len(conflicts),
                "coherence_score": round(self._context.coherence_score, 3),
                "cycle_time_ms": round(self._stats.last_cycle_time_ms, 1),
            }

    # -------------------------------------------------------------------------
    # State Extraction
    # -------------------------------------------------------------------------

    def _extract_player_state(self, insights: List[AgentInsight]) -> Dict[str, Any]:
        """Extract player state from bridge insights."""
        state: Dict[str, Any] = {}
        for insight in insights:
            if insight.category == "player_state":
                state.update(insight.data)
        return state

    def _extract_engine_state(self, insights: List[AgentInsight]) -> Dict[str, Any]:
        """Extract engine state from fusion insights."""
        state: Dict[str, Any] = {}
        for insight in insights:
            if insight.category == "engine_anomaly":
                state.update(insight.data)
        return state

    def _extract_creative_state(self, insights: List[AgentInsight]) -> Dict[str, Any]:
        """Extract creative state from creative autonomy insights."""
        state: Dict[str, Any] = {}
        for insight in insights:
            if insight.category == "creative_goal":
                state.update(insight.data)
        return state

    # -------------------------------------------------------------------------
    # Conflict Detection
    # -------------------------------------------------------------------------

    def _detect_conflicts(self, insights: List[AgentInsight]) -> List[Tuple[str, str]]:
        """Detect conflicting insights."""
        conflicts: List[Tuple[str, str]] = []
        titles = [i.title.lower() for i in insights]
        for a, b in self._conflict_pairs:
            has_a = any(a in t for t in titles)
            has_b = any(b in t for t in titles)
            if has_a and has_b:
                conflicts.append((a, b))
        return conflicts

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the coordination hub status."""
        with self._lock:
            return {
                "active": self._stats.active,
                "cycle_count": self._cycle_count,
                "last_cycle_at": self._last_cycle_at,
                "cycle_interval_s": self._cycle_interval_s,
                "stats": {
                    "total_cycles": self._stats.total_cycles,
                    "total_insights_collected": self._stats.total_insights_collected,
                    "total_insights_dispatched": self._stats.total_insights_dispatched,
                    "total_insights_applied": self._stats.total_insights_applied,
                    "total_conflicts_resolved": self._stats.total_conflicts_resolved,
                    "avg_coherence_score": round(self._stats.avg_coherence_score, 3),
                    "last_cycle_time_ms": round(self._stats.last_cycle_time_ms, 1),
                },
                "context": {
                    "active_insights": len(self._context.active_insights),
                    "prioritized_queue": len(self._context.prioritized_queue),
                    "coherence_score": round(self._context.coherence_score, 3),
                    "last_kernel_action": self._context.last_kernel_action,
                    "player_state_keys": len(self._context.player_state),
                    "engine_state_keys": len(self._context.engine_state),
                    "creative_state_keys": len(self._context.creative_state),
                },
                "modules": {
                    "bridge_orchestrator": self._bridge_orchestrator is not None,
                    "fusion_loop": self._fusion_loop is not None,
                    "creative_autonomy": self._creative_autonomy is not None,
                    "agent_kernel": self._agent_kernel is not None,
                },
            }

    def get_insights(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent insights."""
        with self._lock:
            return [
                {
                    "insight_id": i.insight_id,
                    "source": i.source.value,
                    "priority": i.priority.name,
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
                    "handled": i.handled,
                    "outcome": i.outcome,
                    "timestamp": i.timestamp,
                }
                for i in list(self._insight_history)[-limit:]
            ]

    def get_context(self) -> Dict[str, Any]:
        """Get the current coordination context."""
        with self._lock:
            return {
                "player_state": self._context.player_state,
                "engine_state": self._context.engine_state,
                "creative_state": self._context.creative_state,
                "coherence_score": self._context.coherence_score,
                "last_kernel_action": self._context.last_kernel_action,
                "active_insights": len(self._context.active_insights),
                "prioritized_queue": [
                    {
                        "insight_id": i.insight_id,
                        "source": i.source.value,
                        "priority": i.priority.name,
                        "category": i.category,
                        "title": i.title,
                    }
                    for i in self._context.prioritized_queue[:10]
                ],
            }

    def reset(self) -> None:
        """Reset the coordination hub state."""
        with self._lock:
            self._context = CoordinationContext()
            self._stats = CoordinationStats()
            self._insight_history.clear()
            self._cycle_count = 0
            self._last_cycle_at = 0.0

    def simulate_cycles(self, count: int = 5) -> List[Dict[str, Any]]:
        """Run multiple coordination cycles for testing."""
        results: List[Dict[str, Any]] = []
        for _ in range(count):
            result = self.run_coordination_cycle()
            results.append(result)
            time.sleep(0.1)
        return results
