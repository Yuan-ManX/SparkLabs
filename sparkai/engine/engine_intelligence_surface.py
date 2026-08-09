"""
SparkLabs Engine - Intelligence Surface"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class CapabilityDomain(Enum):
    """Domains of engine capabilities."""
    RENDER = "render"
    PHYSICS = "physics"
    AUDIO = "audio"
    GAMEPLAY = "gameplay"
    WORLD = "world"
    ANIMATION = "animation"
    AI = "ai"
    UI = "ui"
    NETWORK = "network"
    SYSTEM = "system"


class CapabilityStatus(Enum):
    """Status of an engine capability."""
    AVAILABLE = "available"
    BUSY = "busy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class IntentStatus(Enum):
    """Status of a semantic intent execution."""
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EngineCapability:
    """A capability exposed by an engine subsystem."""
    capability_id: str
    name: str
    domain: CapabilityDomain
    description: str
    subsystem: str  # The engine module that implements this
    input_schema: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, str] = field(default_factory=dict)
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    health_score: float = 1.0  # 0.0 to 1.0
    avg_execution_ms: float = 0.0
    total_invocations: int = 0
    success_count: int = 0
    fail_count: int = 0
    last_invoked: float = 0.0
    tags: Set[str] = field(default_factory=set)
    executor: Optional[Callable] = None  # Direct execution function


@dataclass
class SemanticIntent:
    """A semantic request from the agent to the engine."""
    intent_id: str
    action: str  # e.g., "optimize", "generate", "query", "configure"
    target: str  # e.g., "physics", "narrative", "level"
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    status: IntentStatus = IntentStatus.QUEUED
    matched_capability: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class SurfaceStats:
    """Aggregate statistics for the intelligence surface."""
    total_capabilities: int = 0
    available_capabilities: int = 0
    total_intents: int = 0
    total_executed: int = 0
    total_failed: int = 0
    total_queued: int = 0
    avg_match_ms: float = 0.0
    avg_execution_ms: float = 0.0
    intents_by_domain: Dict[str, int] = field(default_factory=dict)
    intents_by_action: Dict[str, int] = field(default_factory=dict)
    last_intent_at: float = 0.0


# =============================================================================
# Engine Intelligence Surface
# =============================================================================

class EngineIntelligenceSurface:
    """
    Singleton semantic interface between the AI agent and the game engine.

    The surface:
      1. Registers engine capabilities with semantic descriptions
      2. Accepts semantic intents from the agent
      3. Matches intents to the correct engine capability
      4. Executes the capability and returns structured results
      5. Tracks performance and health of each capability
    """

    _instance: Optional["EngineIntelligenceSurface"] = None
    _instance_lock = threading.Lock()

    # Action keywords mapped to capability name patterns
    ACTION_MAP: Dict[str, List[str]] = {
        "optimize": ["optim", "tune", "improve", "adjust", "configure"],
        "generate": ["creat", "generat", "build", "make", "produc", "synth"],
        "query": ["get", "query", "list", "status", "check", "inspect"],
        "configure": ["set", "config", "update", "modify", "change"],
        "analyze": ["analyz", "evaluat", "assess", "diagnos", "detect"],
        "execute": ["run", "execut", "trigger", "invoke", "call"],
        "debug": ["debug", "fix", "repair", "heal", "resolve"],
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._capabilities: Dict[str, EngineCapability] = {}
        self._intents: Deque[SemanticIntent] = deque(maxlen=500)
        self._completed_intents: Deque[SemanticIntent] = deque(maxlen=200)
        self._stats = SurfaceStats()
        self._register_default_capabilities()

    @classmethod
    def get_instance(cls) -> "EngineIntelligenceSurface":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Capability Registration
    # -------------------------------------------------------------------------

    def _register_default_capabilities(self) -> None:
        """Register the core engine capabilities."""
        defaults = [
            # RENDER
            ("render_pipeline", "Render Pipeline", CapabilityDomain.RENDER,
             "Execute the rendering pipeline for the current scene",
             "engine_render_pipeline", {"scene_id": "str", "camera": "dict"},
             {"frame": "dict", "draw_calls": "int"}),
            ("lighting_control", "Lighting Control", CapabilityDomain.RENDER,
             "Adjust lighting parameters and bake lightmaps",
             "engine_lighting_director", {"lights": "list", "mode": "str"},
             {"status": "str"}),
            ("post_processing", "Post Processing", CapabilityDomain.RENDER,
             "Apply post-processing effects (bloom, DOF, color grading)",
             "engine_post_processing", {"effects": "list", "intensity": "float"},
             {"status": "str"}),
            # PHYSICS
            ("physics_simulation", "Physics Simulation", CapabilityDomain.PHYSICS,
             "Step the physics simulation forward",
             "engine_physics", {"delta_time": "float", "substeps": "int"},
             {"bodies_updated": "int", "contacts": "int"}),
            ("collision_detection", "Collision Detection", CapabilityDomain.PHYSICS,
             "Detect and resolve collisions between bodies",
             "engine_collision_system", {"bodies": "list"},
             {"collisions": "list"}),
            ("physics_tuning", "Physics Tuning", CapabilityDomain.PHYSICS,
             "Tune physics parameters (gravity, friction, restitution)",
             "engine_physics_dynamics", {"params": "dict"},
             {"applied": "bool"}),
            # AUDIO
            ("audio_playback", "Audio Playback", CapabilityDomain.AUDIO,
             "Play audio clips and manage audio sources",
             "engine_audio_system", {"clip_id": "str", "volume": "float"},
             {"playing": "bool"}),
            ("spatial_audio", "Spatial Audio", CapabilityDomain.AUDIO,
             "Position 3D audio sources in the world",
             "engine_spatial_audio", {"source_id": "str", "position": "dict"},
             {"positioned": "bool"}),
            ("music_director", "Music Director", CapabilityDomain.AUDIO,
             "Manage dynamic music transitions and layers",
             "engine_dynamic_music", {"mood": "str", "intensity": "float"},
             {"transition": "str"}),
            # GAMEPLAY
            ("combat_system", "Combat System", CapabilityDomain.GAMEPLAY,
             "Process combat actions and damage calculations",
             "engine_combat_system", {"attacker": "str", "target": "str", "damage": "float"},
             {"result": "str", "damage_dealt": "float"}),
            ("economy_system", "Economy System", CapabilityDomain.GAMEPLAY,
             "Manage in-game economy, prices, and transactions",
             "engine_economy_system", {"action": "str", "item": "str", "amount": "int"},
             {"balance": "int", "transaction_id": "str"}),
            ("quest_system", "Quest System", CapabilityDomain.GAMEPLAY,
             "Create, update, and complete quests",
             "engine_quest_system", {"quest_id": "str", "action": "str"},
             {"status": "str", "objectives": "list"}),
            ("dialogue_system", "Dialogue System", CapabilityDomain.GAMEPLAY,
             "Run dialogue trees and conversations",
             "engine_dialogue_system", {"dialogue_id": "str", "choice": "int"},
             {"text": "str", "choices": "list"}),
            # WORLD
            ("terrain_generation", "Terrain Generation", CapabilityDomain.WORLD,
             "Generate and sculpt terrain",
             "engine_procedural_terrain", {"size": "dict", "seed": "int", "biome": "str"},
             {"terrain_id": "str", "vertices": "int"}),
            ("weather_control", "Weather Control", CapabilityDomain.WORLD,
             "Set and transition weather states",
             "engine_weather_system", {"weather": "str", "intensity": "float"},
             {"status": "str"}),
            ("biome_generation", "Biome Generation", CapabilityDomain.WORLD,
             "Generate biomes and ecosystems",
             "engine_climate_biome_system", {"region": "dict", "type": "str"},
             {"biome_id": "str", "area": "float"}),
            # ANIMATION
            ("animation_playback", "Animation Playback", CapabilityDomain.ANIMATION,
             "Play and blend animations on skeletal meshes",
             "engine_animation_system", {"entity_id": "str", "anim": "str", "blend": "float"},
             {"playing": "bool"}),
            ("ik_solver", "Inverse Kinematics", CapabilityDomain.ANIMATION,
             "Solve IK chains for foot placement and hand reaching",
             "engine_inverse_kinematics", {"chain": "str", "target": "dict"},
             {"solved": "bool", "joints": "list"}),
            # AI
            ("pathfinding", "Pathfinding", CapabilityDomain.AI,
             "Compute navigation paths",
             "engine_pathfinding", {"start": "dict", "end": "dict", "agent": "str"},
             {"path": "list", "length": "float"}),
            ("behavior_tree", "Behavior Tree", CapabilityDomain.AI,
             "Execute behavior trees for NPCs",
             "engine_behavior_tree", {"npc_id": "str", "tree": "str"},
             {"action": "str", "status": "str"}),
            ("spawn_director", "Spawn Director", CapabilityDomain.AI,
             "Manage enemy spawning and encounter pacing",
             "engine_ai_system", {"zone": "str", "difficulty": "float"},
             {"spawned": "list"}),
            # UI
            ("hud_update", "HUD Update", CapabilityDomain.UI,
             "Update HUD elements (health, score, minimap)",
             "engine_hud_system", {"element": "str", "value": "any"},
             {"updated": "bool"}),
            ("notification", "Notification", CapabilityDomain.UI,
             "Show in-game notifications and toast messages",
             "engine_notification_system", {"message": "str", "type": "str"},
             {"shown": "bool"}),
            # NETWORK
            ("state_replication", "State Replication", CapabilityDomain.NETWORK,
             "Replicate game state to connected clients",
             "engine_network_replication", {"entities": "list", "mode": "str"},
             {"replicated": "int"}),
            ("rpc_call", "RPC Call", CapabilityDomain.NETWORK,
             "Execute remote procedure calls",
             "engine_network_rpc", {"target": "str", "method": "str", "args": "list"},
             {"result": "any"}),
            # SYSTEM
            ("save_game", "Save Game", CapabilityDomain.SYSTEM,
             "Save the current game state",
             "engine_save_system", {"slot": "str"},
             {"saved": "bool", "size": "int"}),
            ("load_game", "Load Game", CapabilityDomain.SYSTEM,
             "Load a saved game state",
             "engine_save_system", {"slot": "str"},
             {"loaded": "bool"}),
            ("analytics_track", "Analytics Tracking", CapabilityDomain.SYSTEM,
             "Track gameplay analytics events",
             "engine_analytics_pipeline", {"event": "str", "data": "dict"},
             {"tracked": "bool"}),
        ]

        for cap_id, name, domain, desc, subsystem, inputs, outputs in defaults:
            cap = EngineCapability(
                capability_id=cap_id,
                name=name,
                domain=domain,
                description=desc,
                subsystem=subsystem,
                input_schema=inputs,
                output_schema=outputs,
            )
            self._capabilities[cap_id] = cap

        self._stats.total_capabilities = len(self._capabilities)
        self._stats.available_capabilities = len(self._capabilities)

    def register_capability(self, cap_id: str, name: str, domain: CapabilityDomain,
                            description: str, subsystem: str,
                            input_schema: Optional[Dict] = None,
                            output_schema: Optional[Dict] = None,
                            executor: Optional[Callable] = None) -> bool:
        """Register a new engine capability."""
        with self._lock:
            self._capabilities[cap_id] = EngineCapability(
                capability_id=cap_id,
                name=name,
                domain=domain,
                description=description,
                subsystem=subsystem,
                input_schema=input_schema or {},
                output_schema=output_schema or {},
                executor=executor,
            )
            self._stats.total_capabilities = len(self._capabilities)
            self._stats.available_capabilities = sum(
                1 for c in self._capabilities.values()
                if c.status == CapabilityStatus.AVAILABLE
            )
            return True

    # -------------------------------------------------------------------------
    # Intent Processing
    # -------------------------------------------------------------------------

    def submit_intent(self, action: str, target: str,
                      parameters: Optional[Dict] = None,
                      description: str = "") -> Dict[str, Any]:
        """
        Submit a semantic intent to the engine.

        Args:
            action: What to do ("optimize", "generate", "query", etc.)
            target: What to act on ("physics", "narrative", "level", etc.)
            parameters: Action-specific parameters
            description: Natural language description

        Returns:
            Dict with intent_id, status, and result (if completed synchronously)
        """
        intent = SemanticIntent(
            intent_id=uuid.uuid4().hex[:12],
            action=action.lower(),
            target=target.lower(),
            parameters=parameters or {},
            description=description,
        )

        with self._lock:
            self._intents.append(intent)
            self._stats.total_intents += 1
            domain_key = target.lower()
            self._stats.intents_by_domain[domain_key] = \
                self._stats.intents_by_domain.get(domain_key, 0) + 1
            action_key = action.lower()
            self._stats.intents_by_action[action_key] = \
                self._stats.intents_by_action.get(action_key, 0) + 1
            self._stats.last_intent_at = time.time()

        # Match and execute
        match_start = time.time()
        capability = self._match_intent(intent)
        match_ms = (time.time() - match_start) * 1000
        if self._stats.avg_match_ms == 0:
            self._stats.avg_match_ms = match_ms
        else:
            self._stats.avg_match_ms = self._stats.avg_match_ms * 0.8 + match_ms * 0.2

        if capability is None:
            intent.status = IntentStatus.FAILED
            intent.error = f"No capability found for {action} {target}"
            with self._lock:
                self._stats.total_failed += 1
                self._completed_intents.append(intent)
            return self._intent_to_dict(intent)

        intent.matched_capability = capability.capability_id
        intent.status = IntentStatus.EXECUTING

        # Execute
        exec_start = time.time()
        success = self._execute_capability(capability, intent)
        exec_ms = (time.time() - exec_start) * 1000
        intent.execution_time_ms = exec_ms
        if self._stats.avg_execution_ms == 0:
            self._stats.avg_execution_ms = exec_ms
        else:
            self._stats.avg_execution_ms = self._stats.avg_execution_ms * 0.8 + exec_ms * 0.2

        with self._lock:
            if success:
                self._stats.total_executed += 1
            else:
                self._stats.total_failed += 1
            self._completed_intents.append(intent)
            try:
                self._intents.remove(intent)
            except ValueError:
                pass

        return self._intent_to_dict(intent)

    def _match_intent(self, intent: SemanticIntent) -> Optional[EngineCapability]:
        """Match a semantic intent to the best engine capability."""
        # Strategy: match by action + target keywords
        action = intent.action
        target = intent.target

        # Map target to domain
        target_to_domain = {
            "physics": CapabilityDomain.PHYSICS,
            "render": CapabilityDomain.RENDER,
            "rendering": CapabilityDomain.RENDER,
            "lighting": CapabilityDomain.RENDER,
            "audio": CapabilityDomain.AUDIO,
            "sound": CapabilityDomain.AUDIO,
            "music": CapabilityDomain.AUDIO,
            "combat": CapabilityDomain.GAMEPLAY,
            "economy": CapabilityDomain.GAMEPLAY,
            "quest": CapabilityDomain.GAMEPLAY,
            "dialogue": CapabilityDomain.GAMEPLAY,
            "narrative": CapabilityDomain.GAMEPLAY,
            "terrain": CapabilityDomain.WORLD,
            "weather": CapabilityDomain.WORLD,
            "biome": CapabilityDomain.WORLD,
            "world": CapabilityDomain.WORLD,
            "level": CapabilityDomain.WORLD,
            "animation": CapabilityDomain.ANIMATION,
            "anim": CapabilityDomain.ANIMATION,
            "pathfinding": CapabilityDomain.AI,
            "nav": CapabilityDomain.AI,
            "npc": CapabilityDomain.AI,
            "ai": CapabilityDomain.AI,
            "hud": CapabilityDomain.UI,
            "ui": CapabilityDomain.UI,
            "menu": CapabilityDomain.UI,
            "network": CapabilityDomain.NETWORK,
            "multiplayer": CapabilityDomain.NETWORK,
            "save": CapabilityDomain.SYSTEM,
            "load": CapabilityDomain.SYSTEM,
            "analytics": CapabilityDomain.SYSTEM,
        }

        # Try exact capability ID match first
        target_lower = target.lower()
        if target_lower in self._capabilities:
            cap = self._capabilities[target_lower]
            if cap.status == CapabilityStatus.AVAILABLE:
                return cap

        # Try action + target combination
        for cap_id, cap in self._capabilities.items():
            if target_lower in cap_id or target_lower in cap.name.lower():
                # Check if the action is relevant
                action_patterns = self.ACTION_MAP.get(action, [])
                if any(p in cap_id or p in cap.name.lower() for p in action_patterns):
                    if cap.status == CapabilityStatus.AVAILABLE:
                        return cap
                # If no action match but target matches, still consider it
                if action in ("query", "execute", "configure"):
                    if cap.status == CapabilityStatus.AVAILABLE:
                        return cap

        # Try domain-based matching
        domain = target_to_domain.get(target_lower)
        if domain:
            domain_caps = [
                c for c in self._capabilities.values()
                if c.domain == domain and c.status == CapabilityStatus.AVAILABLE
            ]
            if domain_caps:
                # Prefer capabilities with the action keyword in their name
                action_patterns = self.ACTION_MAP.get(action, [])
                for cap in domain_caps:
                    if any(p in cap.capability_id or p in cap.name.lower() for p in action_patterns):
                        return cap
                # Return first available in domain
                return domain_caps[0]

        # Fallback: search by tags
        for cap in self._capabilities.values():
            if target_lower in cap.tags and cap.status == CapabilityStatus.AVAILABLE:
                return cap

        return None

    def _execute_capability(self, cap: EngineCapability,
                            intent: SemanticIntent) -> bool:
        """Execute a capability for an intent."""
        cap.total_invocations += 1
        cap.last_invoked = time.time()

        if cap.executor:
            try:
                result = cap.executor(intent.parameters)
                intent.result = result if isinstance(result, dict) else {"output": str(result)}
                intent.status = IntentStatus.COMPLETED
                cap.success_count += 1
                return True
            except Exception as e:
                logger.error("Capability %s failed: %s", cap.capability_id, e)
                intent.error = str(e)
                intent.status = IntentStatus.FAILED
                cap.fail_count += 1
                return False
        else:
            # Simulated execution (no real executor registered)
            intent.result = {
                "capability": cap.capability_id,
                "subsystem": cap.subsystem,
                "action": intent.action,
                "target": intent.target,
                "parameters": intent.parameters,
                "simulated": True,
            }
            intent.status = IntentStatus.COMPLETED
            cap.success_count += 1
            return True

    # -------------------------------------------------------------------------
    # Query API
    # -------------------------------------------------------------------------

    def get_capabilities(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all capabilities, optionally filtered by domain."""
        with self._lock:
            caps = list(self._capabilities.values())
            if domain:
                dom = CapabilityDomain(domain)
                caps = [c for c in caps if c.domain == dom]
            return [self._capability_to_dict(c) for c in caps]

    def get_capability(self, cap_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific capability by ID."""
        with self._lock:
            cap = self._capabilities.get(cap_id)
            if cap:
                return self._capability_to_dict(cap)
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get the surface status."""
        with self._lock:
            return {
                "stats": {
                    "total_capabilities": self._stats.total_capabilities,
                    "available_capabilities": self._stats.available_capabilities,
                    "total_intents": self._stats.total_intents,
                    "total_executed": self._stats.total_executed,
                    "total_failed": self._stats.total_failed,
                    "total_queued": self._stats.total_queued,
                    "avg_match_ms": round(self._stats.avg_match_ms, 2),
                    "avg_execution_ms": round(self._stats.avg_execution_ms, 2),
                    "last_intent_at": self._stats.last_intent_at,
                },
                "intents_by_domain": dict(self._stats.intents_by_domain),
                "intents_by_action": dict(self._stats.intents_by_action),
                "capabilities_by_domain": self._capabilities_by_domain(),
            }

    def get_recent_intents(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent intents."""
        with self._lock:
            recent = list(self._completed_intents)[-limit:]
            pending = list(self._intents)
            all_intents = pending + recent
            all_intents.sort(key=lambda i: i.timestamp, reverse=True)
            return [self._intent_to_dict(i) for i in all_intents[:limit]]

    def get_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific intent by ID."""
        with self._lock:
            for i in self._intents:
                if i.intent_id == intent_id:
                    return self._intent_to_dict(i)
            for i in self._completed_intents:
                if i.intent_id == intent_id:
                    return self._intent_to_dict(i)
        return None

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def simulate_intents(self, count: int = 10) -> Dict[str, Any]:
        """Simulate semantic intents for testing."""
        import random
        actions = ["optimize", "generate", "query", "configure", "analyze", "execute"]
        targets = ["physics", "render", "audio", "combat", "terrain", "animation",
                   "pathfinding", "hud", "network", "save"]
        results = []
        for _ in range(count):
            action = random.choice(actions)
            target = random.choice(targets)
            result = self.submit_intent(
                action, target,
                {"description": f"Simulated {action} {target}"},
                f"Simulated intent: {action} {target}",
            )
            results.append(result)
        return {
            "total": len(results),
            "completed": sum(1 for r in results if r.get("status") == "completed"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "results": results,
        }

    def reset(self) -> None:
        """Reset the surface state."""
        with self._lock:
            self._intents.clear()
            self._completed_intents.clear()
            self._stats = SurfaceStats()
            self._stats.total_capabilities = len(self._capabilities)
            self._stats.available_capabilities = sum(
                1 for c in self._capabilities.values()
                if c.status == CapabilityStatus.AVAILABLE
            )
            for cap in self._capabilities.values():
                cap.total_invocations = 0
                cap.success_count = 0
                cap.fail_count = 0
                cap.avg_execution_ms = 0.0

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _capabilities_by_domain(self) -> Dict[str, int]:
        """Count capabilities per domain."""
        counts: Dict[str, int] = {}
        for cap in self._capabilities.values():
            key = cap.domain.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _capability_to_dict(self, c: EngineCapability) -> Dict[str, Any]:
        """Convert a capability to a dictionary."""
        return {
            "capability_id": c.capability_id,
            "name": c.name,
            "domain": c.domain.value,
            "description": c.description,
            "subsystem": c.subsystem,
            "input_schema": c.input_schema,
            "output_schema": c.output_schema,
            "status": c.status.value,
            "health_score": round(c.health_score, 3),
            "avg_execution_ms": round(c.avg_execution_ms, 2),
            "total_invocations": c.total_invocations,
            "success_count": c.success_count,
            "fail_count": c.fail_count,
            "success_rate": round(c.success_count / max(1, c.total_invocations), 3),
            "last_invoked": c.last_invoked,
            "tags": sorted(c.tags),
        }

    def _intent_to_dict(self, i: SemanticIntent) -> Dict[str, Any]:
        """Convert an intent to a dictionary."""
        return {
            "intent_id": i.intent_id,
            "action": i.action,
            "target": i.target,
            "parameters": i.parameters,
            "description": i.description,
            "timestamp": i.timestamp,
            "status": i.status.value,
            "matched_capability": i.matched_capability,
            "result": i.result,
            "error": i.error,
            "execution_time_ms": round(i.execution_time_ms, 2),
        }


# =============================================================================
# Module-level singleton accessor
# =============================================================================

def get_intelligence_surface() -> EngineIntelligenceSurface:
    """Return the singleton intelligence surface instance."""
    return EngineIntelligenceSurface.get_instance()
