"""
SparkLabs Agent - Cognitive Mesh"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class NodeType(Enum):
    """Type of mesh node."""
    AGENT = "agent"        # An agent module that can process signals
    ENGINE = "engine"      # An engine subsystem that produces signals
    BRIDGE = "bridge"      # A bidirectional bridge between agent and engine
    ORCHESTRATOR = "orchestrator"  # A coordinating node


class SignalType(Enum):
    """Types of cognitive signals that flow through the mesh."""
    ANOMALY = "anomaly"            # Unexpected behavior detected
    OPPORTUNITY = "opportunity"    # Creative/optimization opportunity
    REQUEST = "request"            # Subsystem requesting AI assistance
    DECISION = "decision"          # Agent decision for engine execution
    FEEDBACK = "feedback"          # Outcome of a previous decision
    TELEMETRY = "telemetry"        # Routine status update
    ALERT = "alert"                # Urgent issue requiring attention


class SignalPriority(Enum):
    """Priority levels for signal routing."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4


class MeshPhase(Enum):
    """Phases of the cognitive mesh cycle."""
    COLLECT = "collect"
    ROUTE = "route"
    DISPATCH = "dispatch"
    EXECUTE = "execute"
    FEEDBACK = "feedback"
    LEARN = "learn"


class SignalStatus(Enum):
    """Status of a signal as it flows through the mesh."""
    PENDING = "pending"
    ROUTED = "routed"
    DISPATCHED = "dispatched"
    EXECUTED = "executed"
    COMPLETED = "completed"
    FAILED = "failed"
    DROPPED = "dropped"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MeshNode:
    """A node in the cognitive mesh."""
    node_id: str
    name: str
    node_type: NodeType
    capabilities: Set[str] = field(default_factory=set)
    priority: float = 1.0  # Higher = preferred handler
    active: bool = True
    signal_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    avg_latency_ms: float = 0.0
    last_active: float = 0.0
    handler: Optional[Callable] = None  # Optional direct handler


@dataclass
class CognitiveSignal:
    """A signal flowing through the cognitive mesh."""
    signal_id: str
    signal_type: SignalType
    priority: SignalPriority
    source_node: str
    target_node: Optional[str] = None  # None = route to best handler
    category: str = ""  # Sub-category (e.g., "physics", "narrative", "balance")
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    status: SignalStatus = SignalStatus.PENDING
    routed_to: Optional[str] = None
    dispatched_at: Optional[float] = None
    completed_at: Optional[float] = None
    outcome: Optional[str] = None  # "success", "failure", "partial"
    result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshStats:
    """Aggregate statistics for the mesh."""
    total_signals: int = 0
    total_routed: int = 0
    total_dispatched: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_dropped: int = 0
    total_cycles: int = 0
    avg_cycle_ms: float = 0.0
    success_rate: float = 0.0
    active_nodes: int = 0
    total_nodes: int = 0
    signals_by_type: Dict[str, int] = field(default_factory=dict)
    signals_by_category: Dict[str, int] = field(default_factory=dict)
    last_cycle_at: float = 0.0
    cycle_interval_s: float = 2.0


@dataclass
class RoutingRule:
    """A rule for routing signals to handlers."""
    rule_id: str
    signal_type: Optional[SignalType] = None  # None = match any
    category: Optional[str] = None  # None = match any
    target_node_id: str = ""
    priority_boost: float = 0.0
    enabled: bool = True


# =============================================================================
# Cognitive Mesh
# =============================================================================

class AgentCognitiveMesh:
    """
    Singleton bidirectional intelligence fabric between agent and engine.

    The mesh:
      1. Registers nodes (agent modules + engine subsystems)
      2. Collects cognitive signals from all nodes
      3. Routes each signal to the optimal handler
      4. Dispatches and tracks execution
      5. Collects feedback and updates routing intelligence
      6. Learns which handlers work best for each signal type
    """

    _instance: Optional["AgentCognitiveMesh"] = None
    _instance_lock = threading.Lock()

    # Default routing: signal_type/category -> preferred node capabilities
    DEFAULT_ROUTING: Dict[Tuple[str, str], List[str]] = {
        ("anomaly", "physics"): ["physics_tuner", "adaptive_physics", "bug_hunter"],
        ("anomaly", "performance"): ["performance_optimizer", "performance_advisor"],
        ("anomaly", "balance"): ["balance_analyzer", "balance_optimizer", "game_critic"],
        ("anomaly", "bug"): ["bug_hunter", "bug_forensics", "game_healer"],
        ("anomaly", "crash"): ["bug_hunter", "game_healer", "crash_reporter"],
        ("opportunity", "narrative"): ["narrative_composer", "story_forge", "creative_director"],
        ("opportunity", "content"): ["content_forge", "content_synthesis", "game_forge"],
        ("opportunity", "level"): ["level_designer", "procedural_dungeon", "world_architect"],
        ("opportunity", "visual"): ["cinematographer", "visual_composer", "photo_director"],
        ("opportunity", "audio"): ["audio_composer", "music_composer", "voice_synthesizer"],
        ("opportunity", "gameplay"): ["game_designer", "game_director", "creative_autonomy"],
        ("request", "code"): ["code_generator", "agentic_coding", "developer_assistant"],
        ("request", "asset"): ["asset_synthesizer", "asset_optimizer", "asset_harmonizer"],
        ("request", "test"): ["playtest_simulator", "autonomous_tester", "quality_assurance"],
        ("request", "optimize"): ["performance_optimizer", "self_optimization", "game_polish"],
        ("request", "balance"): ["balance_optimizer", "dynamic_difficulty", "adaptive_director"],
        ("request", "narrative"): ["narrative_engine", "dialogue_engine", "quest_generator"],
        ("alert", "security"): ["security_scanner", "anti_cheat", "content_moderation"],
        ("alert", "performance"): ["performance_optimizer", "performance_advisor"],
        ("alert", "stability"): ["game_healer", "game_sentinel", "crash_reporter"],
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._nodes: Dict[str, MeshNode] = {}
        self._signals: Deque[CognitiveSignal] = deque(maxlen=500)
        self._completed_signals: Deque[CognitiveSignal] = deque(maxlen=200)
        self._routing_rules: Dict[str, RoutingRule] = {}
        self._stats = MeshStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._cycle_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Learning: track success rates per (signal_type, category, handler)
        self._routing_intelligence: Dict[str, Dict[str, float]] = {}
        # Key: f"{signal_type}:{category}", Value: {node_id: success_rate}

        # Register default nodes
        self._register_default_nodes()

    @classmethod
    def get_instance(cls) -> "AgentCognitiveMesh":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Node Registration
    # -------------------------------------------------------------------------

    def _register_default_nodes(self) -> None:
        """Register the core mesh nodes."""
        default_nodes = [
            ("coordination_hub", "Coordination Hub", NodeType.ORCHESTRATOR,
             {"coordinate", "synthesize", "prioritize", "dispatch"}),
            ("bridge_orchestrator", "Bridge Orchestrator", NodeType.BRIDGE,
             {"player_model", "telemetry", "directives", "churn_detection"}),
            ("fusion_loop", "Engine Fusion Loop", NodeType.BRIDGE,
             {"engine_monitor", "anomaly_detection", "goal_synthesis"}),
            ("creative_autonomy", "Creative Autonomy", NodeType.AGENT,
             {"creative", "pattern_detection", "intervention"}),
            ("playtest_simulator", "Playtest Simulator", NodeType.AGENT,
             {"playtest", "virtual_players", "issue_detection", "scoring"}),
            ("llm_router", "LLM Router", NodeType.AGENT,
             {"llm", "model_routing", "text_gen", "code_gen", "asset_gen"}),
            ("chat_editor_bridge", "Chat-Editor Bridge", NodeType.BRIDGE,
             {"chat", "editor_control", "action_classification"}),
            ("cognitive_kernel", "Cognitive Kernel", NodeType.ORCHESTRATOR,
             {"reasoning", "memory", "learning", "planning"}),
        ]
        for node_id, name, ntype, caps in default_nodes:
            node = MeshNode(
                node_id=node_id,
                name=name,
                node_type=ntype,
                capabilities=set(caps),
            )
            self._nodes[node_id] = node

        self._stats.total_nodes = len(self._nodes)
        self._stats.active_nodes = len(self._nodes)

    def register_node(self, node_id: str, name: str, node_type: NodeType,
                      capabilities: Set[str], handler: Optional[Callable] = None) -> bool:
        """Register a new node in the mesh."""
        with self._lock:
            if node_id in self._nodes:
                logger.warning("Node %s already registered, updating", node_id)
            self._nodes[node_id] = MeshNode(
                node_id=node_id,
                name=name,
                node_type=node_type,
                capabilities=capabilities,
                handler=handler,
            )
            self._stats.total_nodes = len(self._nodes)
            self._stats.active_nodes = sum(1 for n in self._nodes.values() if n.active)
            logger.info("Registered mesh node: %s (%s)", node_id, name)
            return True

    def unregister_node(self, node_id: str) -> bool:
        """Remove a node from the mesh."""
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].active = False
                self._stats.active_nodes = sum(1 for n in self._nodes.values() if n.active)
                return True
            return False

    # -------------------------------------------------------------------------
    # Signal Management
    # -------------------------------------------------------------------------

    def emit_signal(self, signal_type: SignalType, category: str,
                    source_node: str, payload: Optional[Dict] = None,
                    priority: SignalPriority = SignalPriority.NORMAL,
                    target_node: Optional[str] = None) -> str:
        """
        Emit a cognitive signal into the mesh.

        Returns the signal_id for tracking.
        """
        signal = CognitiveSignal(
            signal_id=uuid.uuid4().hex[:12],
            signal_type=signal_type,
            priority=priority,
            source_node=source_node,
            target_node=target_node,
            category=category,
            payload=payload or {},
        )
        with self._lock:
            self._signals.append(signal)
            self._stats.total_signals += 1
            type_key = signal_type.value
            self._stats.signals_by_type[type_key] = \
                self._stats.signals_by_type.get(type_key, 0) + 1
            cat_key = category
            self._stats.signals_by_category[cat_key] = \
                self._stats.signals_by_category.get(cat_key, 0) + 1
        return signal.signal_id

    def get_pending_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get pending signals."""
        with self._lock:
            pending = [s for s in self._signals if s.status == SignalStatus.PENDING]
            return [self._signal_to_dict(s) for s in pending[:limit]]

    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific signal by ID."""
        with self._lock:
            for s in self._signals:
                if s.signal_id == signal_id:
                    return self._signal_to_dict(s)
            for s in self._completed_signals:
                if s.signal_id == signal_id:
                    return self._signal_to_dict(s)
        return None

    # -------------------------------------------------------------------------
    # Signal Routing
    # -------------------------------------------------------------------------

    def _route_signal(self, signal: CognitiveSignal) -> Optional[str]:
        """
        Route a signal to the best handler node.

        Routing priority:
          1. Explicit target_node if specified
          2. Custom routing rules
          3. Default routing table based on signal_type + category
          4. Learning-based routing (highest success rate)
          5. Fallback to coordination_hub
        """
        # 1. Explicit target
        if signal.target_node and signal.target_node in self._nodes:
            node = self._nodes[signal.target_node]
            if node.active:
                return signal.target_node

        # 2. Custom routing rules
        for rule in self._routing_rules.values():
            if not rule.enabled:
                continue
            if rule.signal_type and rule.signal_type != signal.signal_type:
                continue
            if rule.category and rule.category != signal.category:
                continue
            if rule.target_node_id in self._nodes and self._nodes[rule.target_node_id].active:
                return rule.target_node_id

        # 3. Default routing table
        routing_key = (signal.signal_type.value, signal.category)
        preferred_caps = self.DEFAULT_ROUTING.get(routing_key, [])

        # 4. Learning-based: check success rates
        intel_key = f"{signal.signal_type.value}:{signal.category}"
        intel = self._routing_intelligence.get(intel_key, {})

        # Build candidate list from default routing + learning
        candidates: List[Tuple[str, float]] = []
        for cap in preferred_caps:
            # Find nodes with this capability
            for node_id, node in self._nodes.items():
                if not node.active:
                    continue
                if cap in node.capabilities or cap in node_id:
                    score = node.priority
                    # Boost by learned success rate
                    learned_rate = intel.get(node_id, 0.5)
                    score *= (0.5 + learned_rate)
                    candidates.append((node_id, score))

        # Also check learning for nodes not in default routing
        for node_id, rate in intel.items():
            if node_id in self._nodes and self._nodes[node_id].active:
                if node_id not in [c[0] for c in candidates]:
                    candidates.append((node_id, rate * self._nodes[node_id].priority))

        if candidates:
            # Sort by score descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # 5. Fallback to coordination hub
        if "coordination_hub" in self._nodes and self._nodes["coordination_hub"].active:
            return "coordination_hub"

        return None

    def _dispatch_signal(self, signal: CognitiveSignal, handler_node_id: str) -> bool:
        """Dispatch a signal to its handler node."""
        node = self._nodes.get(handler_node_id)
        if not node or not node.active:
            return False

        start_time = time.time()
        signal.routed_to = handler_node_id
        signal.status = SignalStatus.DISPATCHED
        signal.dispatched_at = time.time()
        node.signal_count += 1
        node.last_active = time.time()

        # If the node has a direct handler, call it
        if node.handler:
            try:
                result = node.handler(signal.payload)
                signal.result = result if isinstance(result, dict) else {"output": str(result)}
                signal.status = SignalStatus.COMPLETED
                signal.completed_at = time.time()
                signal.outcome = "success"
                node.success_count += 1
                self._update_learning(signal, handler_node_id, True)
            except Exception as e:
                logger.error("Handler %s failed: %s", handler_node_id, e)
                signal.status = SignalStatus.FAILED
                signal.outcome = "failure"
                signal.result = {"error": str(e)}
                node.fail_count += 1
                self._update_learning(signal, handler_node_id, False)
        else:
            # No direct handler - simulate successful dispatch
            signal.status = SignalStatus.COMPLETED
            signal.completed_at = time.time()
            signal.outcome = "success"
            signal.result = {"dispatched": True, "handler": handler_node_id}
            node.success_count += 1
            self._update_learning(signal, handler_node_id, True)

        # Update node latency
        latency = (time.time() - start_time) * 1000
        if node.avg_latency_ms == 0:
            node.avg_latency_ms = latency
        else:
            node.avg_latency_ms = node.avg_latency_ms * 0.8 + latency * 0.2

        return True

    def _update_learning(self, signal: CognitiveSignal, handler_id: str, success: bool) -> None:
        """Update routing intelligence based on outcome."""
        intel_key = f"{signal.signal_type.value}:{signal.category}"
        if intel_key not in self._routing_intelligence:
            self._routing_intelligence[intel_key] = {}
        intel = self._routing_intelligence[intel_key]
        current = intel.get(handler_id, 0.5)
        # Exponential moving average
        if success:
            intel[handler_id] = current * 0.7 + 0.3
        else:
            intel[handler_id] = current * 0.7
        # Cap at 1.0
        intel[handler_id] = min(1.0, max(0.0, intel[handler_id]))

    # -------------------------------------------------------------------------
    # Cognitive Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run a single cognitive mesh cycle:
          COLLECT -> ROUTE -> DISPATCH -> EXECUTE -> FEEDBACK -> LEARN
        """
        cycle_start = time.time()
        results = {
            "collected": 0,
            "routed": 0,
            "dispatched": 0,
            "completed": 0,
            "failed": 0,
            "dropped": 0,
        }

        with self._lock:
            pending = [s for s in self._signals if s.status == SignalStatus.PENDING]
            results["collected"] = len(pending)

            # Sort by priority (highest first)
            pending.sort(key=lambda s: s.priority.value, reverse=True)

            for signal in pending:
                # Route
                handler_id = self._route_signal(signal)
                if handler_id is None:
                    signal.status = SignalStatus.DROPPED
                    results["dropped"] += 1
                    self._stats.total_dropped += 1
                    continue

                signal.status = SignalStatus.ROUTED
                results["routed"] += 1
                self._stats.total_routed += 1

                # Dispatch
                success = self._dispatch_signal(signal, handler_id)
                if success:
                    results["dispatched"] += 1
                    self._stats.total_dispatched += 1
                    if signal.status == SignalStatus.COMPLETED:
                        results["completed"] += 1
                        self._stats.total_completed += 1
                    elif signal.status == SignalStatus.FAILED:
                        results["failed"] += 1
                        self._stats.total_failed += 1
                else:
                    signal.status = SignalStatus.FAILED
                    results["failed"] += 1
                    self._stats.total_failed += 1

                # Move completed signals to history
                if signal.status in (SignalStatus.COMPLETED, SignalStatus.FAILED):
                    self._completed_signals.append(signal)
                    # Remove from active signals
                    try:
                        self._signals.remove(signal)
                    except ValueError:
                        pass

            # Update stats
            self._cycle_count += 1
            self._stats.total_cycles = self._cycle_count
            cycle_ms = (time.time() - cycle_start) * 1000
            if self._stats.avg_cycle_ms == 0:
                self._stats.avg_cycle_ms = cycle_ms
            else:
                self._stats.avg_cycle_ms = self._stats.avg_cycle_ms * 0.8 + cycle_ms * 0.2
            self._stats.last_cycle_at = time.time()

            total = self._stats.total_completed + self._stats.total_failed
            if total > 0:
                self._stats.success_rate = self._stats.total_completed / total

        return results

    def start(self) -> None:
        """Start the automatic cognitive cycle."""
        if self._active:
            return
        self._active = True
        self._stop_event.clear()
        self._cycle_thread = threading.Thread(
            target=self._cycle_loop, daemon=True, name="cognitive-mesh"
        )
        self._cycle_thread.start()
        logger.info("Cognitive mesh started")

    def stop(self) -> None:
        """Stop the automatic cognitive cycle."""
        self._active = False
        self._stop_event.set()
        if self._cycle_thread:
            self._cycle_thread.join(timeout=2.0)
        logger.info("Cognitive mesh stopped")

    def _cycle_loop(self) -> None:
        """Background loop that runs cognitive cycles."""
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                logger.error("Cognitive mesh cycle error: %s", e)
            self._stop_event.wait(self._stats.cycle_interval_s)

    # -------------------------------------------------------------------------
    # Signal Injection Helpers
    # -------------------------------------------------------------------------

    def report_anomaly(self, source: str, category: str, description: str,
                       severity: str = "normal", payload: Optional[Dict] = None) -> str:
        """Report an anomaly detected by an engine subsystem."""
        priority_map = {
            "low": SignalPriority.LOW,
            "normal": SignalPriority.NORMAL,
            "high": SignalPriority.HIGH,
            "urgent": SignalPriority.URGENT,
            "critical": SignalPriority.CRITICAL,
        }
        data = {"description": description}
        if payload:
            data.update(payload)
        return self.emit_signal(
            SignalType.ANOMALY, category, source, data,
            priority_map.get(severity, SignalPriority.NORMAL),
        )

    def report_opportunity(self, source: str, category: str, description: str,
                           payload: Optional[Dict] = None) -> str:
        """Report a creative or optimization opportunity."""
        data = {"description": description}
        if payload:
            data.update(payload)
        return self.emit_signal(
            SignalType.OPPORTUNITY, category, source, data,
            SignalPriority.NORMAL,
        )

    def request_assistance(self, source: str, category: str, request: str,
                           payload: Optional[Dict] = None) -> str:
        """Request AI assistance for a subsystem."""
        data = {"request": request}
        if payload:
            data.update(payload)
        return self.emit_signal(
            SignalType.REQUEST, category, source, data,
            SignalPriority.HIGH,
        )

    def send_feedback(self, source: str, signal_id: str, outcome: str,
                      result: Optional[Dict] = None) -> None:
        """Send feedback about a previous decision."""
        with self._lock:
            for s in self._completed_signals:
                if s.signal_id == signal_id:
                    s.outcome = outcome
                    if result:
                        s.result.update(result)
                    # Update learning
                    if s.routed_to:
                        self._update_learning(s, s.routed_to, outcome == "success")
                    break

    # -------------------------------------------------------------------------
    # Status and Query API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the mesh status."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "last_cycle_at": self._stats.last_cycle_at,
                "cycle_interval_s": self._stats.cycle_interval_s,
                "stats": {
                    "total_signals": self._stats.total_signals,
                    "total_routed": self._stats.total_routed,
                    "total_dispatched": self._stats.total_dispatched,
                    "total_completed": self._stats.total_completed,
                    "total_failed": self._stats.total_failed,
                    "total_dropped": self._stats.total_dropped,
                    "total_cycles": self._stats.total_cycles,
                    "avg_cycle_ms": round(self._stats.avg_cycle_ms, 2),
                    "success_rate": round(self._stats.success_rate, 3),
                    "active_nodes": self._stats.active_nodes,
                    "total_nodes": self._stats.total_nodes,
                    "pending_signals": sum(1 for s in self._signals if s.status == SignalStatus.PENDING),
                },
                "signals_by_type": dict(self._stats.signals_by_type),
                "signals_by_category": dict(self._stats.signals_by_category),
            }

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get all registered nodes."""
        with self._lock:
            return [
                {
                    "node_id": n.node_id,
                    "name": n.name,
                    "node_type": n.node_type.value,
                    "capabilities": sorted(n.capabilities),
                    "priority": n.priority,
                    "active": n.active,
                    "signal_count": n.signal_count,
                    "success_count": n.success_count,
                    "fail_count": n.fail_count,
                    "success_rate": round(n.success_count / max(1, n.signal_count), 3),
                    "avg_latency_ms": round(n.avg_latency_ms, 2),
                    "last_active": n.last_active,
                }
                for n in self._nodes.values()
            ]

    def get_recent_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent signals (both pending and completed)."""
        with self._lock:
            recent = list(self._completed_signals)[-limit:]
            pending = [s for s in self._signals if s.status == SignalStatus.PENDING]
            all_signals = pending + recent
            all_signals.sort(key=lambda s: s.timestamp, reverse=True)
            return [self._signal_to_dict(s) for s in all_signals[:limit]]

    def get_routing_intelligence(self) -> Dict[str, Any]:
        """Get the learned routing intelligence."""
        with self._lock:
            return {
                key: {k: round(v, 3) for k, v in vals.items()}
                for key, vals in self._routing_intelligence.items()
            }

    def add_routing_rule(self, rule_id: str, target_node_id: str,
                         signal_type: Optional[str] = None,
                         category: Optional[str] = None,
                         priority_boost: float = 0.0) -> bool:
        """Add a custom routing rule."""
        with self._lock:
            st = SignalType(signal_type) if signal_type else None
            self._routing_rules[rule_id] = RoutingRule(
                rule_id=rule_id,
                signal_type=st,
                category=category,
                target_node_id=target_node_id,
                priority_boost=priority_boost,
            )
            return True

    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule."""
        with self._lock:
            if rule_id in self._routing_rules:
                del self._routing_rules[rule_id]
                return True
            return False

    # -------------------------------------------------------------------------
    # Simulation (for testing without real modules)
    # -------------------------------------------------------------------------

    def simulate_traffic(self, count: int = 10) -> Dict[str, Any]:
        """Simulate cognitive signals for testing."""
        import random
        categories = ["physics", "narrative", "balance", "performance", "content",
                      "level", "visual", "audio", "code", "test"]
        signal_types = [SignalType.ANOMALY, SignalType.OPPORTUNITY,
                        SignalType.REQUEST, SignalType.TELEMETRY]
        priorities = [SignalPriority.LOW, SignalPriority.NORMAL,
                      SignalPriority.HIGH, SignalPriority.URGENT]
        sources = list(self._nodes.keys())

        emitted = []
        for _ in range(count):
            st = random.choice(signal_types)
            cat = random.choice(categories)
            src = random.choice(sources)
            sid = self.emit_signal(
                st, cat, src,
                {"description": f"Simulated {st.value} in {cat}"},
                random.choice(priorities),
            )
            emitted.append(sid)

        # Run a cycle to process them
        cycle_result = self.run_cycle()
        return {
            "emitted": len(emitted),
            "signal_ids": emitted,
            "cycle_result": cycle_result,
        }

    def reset(self) -> None:
        """Reset the mesh state."""
        with self._lock:
            self._signals.clear()
            self._completed_signals.clear()
            self._routing_intelligence.clear()
            self._stats = MeshStats()
            self._stats.total_nodes = len(self._nodes)
            self._stats.active_nodes = sum(1 for n in self._nodes.values() if n.active)
            self._cycle_count = 0
            for node in self._nodes.values():
                node.signal_count = 0
                node.success_count = 0
                node.fail_count = 0
                node.avg_latency_ms = 0.0

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _signal_to_dict(self, s: CognitiveSignal) -> Dict[str, Any]:
        """Convert a signal to a dictionary."""
        return {
            "signal_id": s.signal_id,
            "signal_type": s.signal_type.value,
            "priority": s.priority.name,
            "source_node": s.source_node,
            "target_node": s.target_node,
            "routed_to": s.routed_to,
            "category": s.category,
            "status": s.status.value,
            "outcome": s.outcome,
            "timestamp": s.timestamp,
            "dispatched_at": s.dispatched_at,
            "completed_at": s.completed_at,
            "payload": s.payload,
            "result": s.result,
        }


# =============================================================================
# Module-level singleton accessor
# =============================================================================

def get_cognitive_mesh() -> AgentCognitiveMesh:
    """Return the singleton cognitive mesh instance."""
    return AgentCognitiveMesh.get_instance()
