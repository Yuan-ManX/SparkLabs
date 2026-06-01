"""
SparkAI Agent - Interaction Synthesis Engine

An autonomous system that transforms high-level gameplay descriptions
into complete, executable interaction systems. The synthesis engine
understands game design principles and generates cohesive interaction
networks that combine mechanics, physics, input handling, feedback,
and progression into unified gameplay loops.

Key capabilities:
  - Interaction network synthesis from natural language
  - Mechanic-to-physics parameter mapping
  - Input-to-action binding generation
  - Progression curve computation with difficulty scaling
  - Feedback system orchestration (visual, audio, haptic)
  - Interaction conflict detection and resolution
  - Gameplay loop flow validation

Architecture:
  InteractionSynthesisEngine (Singleton)
    |-- InteractionConcept (dataclass)
    |-- InteractionNetwork (dataclass)
    |-- ProgressionProfile (dataclass)
    |-- synthesize_interaction_network()
    |-- compute_progression_curve()
    |-- detect_interaction_conflicts()
    |-- generate_feedback_spec()
    |-- validate_loop_integrity()
"""

from __future__ import annotations

import time as _time_module
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class InteractionDomain(Enum):
    MOVEMENT = "movement"
    COMBAT = "combat"
    PUZZLE = "puzzle"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    RESOURCE = "resource"
    BUILDING = "building"
    STEALTH = "stealth"
    NARRATIVE = "narrative"
    CUSTOM = "custom"


class FeedbackChannel(Enum):
    VISUAL = "visual"
    AUDIO = "audio"
    HAPTIC = "haptic"
    UI = "ui"
    CAMERA = "camera"
    PARTICLE = "particle"
    NARRATIVE = "narrative"


class ConflictSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class InteractionConcept:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    domain: InteractionDomain = InteractionDomain.CUSTOM
    description: str = ""
    primary_action: str = ""
    input_binding: str = ""
    physics_properties: Dict[str, Any] = field(default_factory=dict)
    prerequisite_interactions: List[str] = field(default_factory=list)
    feedback_channels: List[FeedbackChannel] = field(default_factory=list)
    cooldown_ms: int = 0
    energy_cost: float = 0.0
    complexity_rating: float = 0.5
    synergy_tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "description": self.description,
            "primary_action": self.primary_action,
            "input_binding": self.input_binding,
            "physics_properties": self.physics_properties,
            "prerequisite_interactions": self.prerequisite_interactions,
            "feedback_channels": [ch.value for ch in self.feedback_channels],
            "cooldown_ms": self.cooldown_ms,
            "energy_cost": self.energy_cost,
            "complexity_rating": self.complexity_rating,
            "synergy_tags": self.synergy_tags,
            "created_at": self.created_at,
        }


@dataclass
class InteractionNetwork:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    interactions: List[InteractionConcept] = field(default_factory=list)
    adjacency_map: Dict[str, List[str]] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    cycle_graph: List[List[str]] = field(default_factory=list)
    network_density: float = 0.0
    overall_complexity: float = 0.5
    cohesion_score: float = 0.5
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "interaction_count": len(self.interactions),
            "interactions": [i.to_dict() for i in self.interactions],
            "adjacency_map": self.adjacency_map,
            "entry_points": self.entry_points,
            "cycle_graph": self.cycle_graph,
            "network_density": self.network_density,
            "overall_complexity": self.overall_complexity,
            "cohesion_score": self.cohesion_score,
            "generated_at": self.generated_at,
        }


@dataclass
class ProgressionProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    interaction_id: str = ""
    scaling_curve: str = "linear"
    initial_difficulty: float = 0.3
    final_difficulty: float = 0.9
    scaling_factors: Dict[str, float] = field(default_factory=dict)
    unlock_conditions: Dict[str, Any] = field(default_factory=dict)
    mastery_thresholds: List[float] = field(default_factory=list)
    computed_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "interaction_id": self.interaction_id,
            "scaling_curve": self.scaling_curve,
            "initial_difficulty": self.initial_difficulty,
            "final_difficulty": self.final_difficulty,
            "scaling_factors": self.scaling_factors,
            "unlock_conditions": self.unlock_conditions,
            "mastery_thresholds": self.mastery_thresholds,
            "computed_at": self.computed_at,
        }


@dataclass
class ConflictReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    interaction_a: str = ""
    interaction_b: str = ""
    severity: ConflictSeverity = ConflictSeverity.INFO
    description: str = ""
    suggested_resolution: str = ""
    domain_overlap: float = 0.0
    resource_conflict: bool = False
    timing_conflict: bool = False
    input_conflict: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "interaction_a": self.interaction_a,
            "interaction_b": self.interaction_b,
            "severity": self.severity.value,
            "description": self.description,
            "suggested_resolution": self.suggested_resolution,
            "domain_overlap": self.domain_overlap,
            "resource_conflict": self.resource_conflict,
            "timing_conflict": self.timing_conflict,
            "input_conflict": self.input_conflict,
        }


@dataclass
class FeedbackSpec:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    interaction_id: str = ""
    channel: FeedbackChannel = FeedbackChannel.VISUAL
    trigger_event: str = ""
    duration_ms: int = 500
    intensity: float = 0.7
    parameters: Dict[str, Any] = field(default_factory=dict)
    cooldown_ms: int = 200

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "interaction_id": self.interaction_id,
            "channel": self.channel.value,
            "trigger_event": self.trigger_event,
            "duration_ms": self.duration_ms,
            "intensity": self.intensity,
            "parameters": self.parameters,
            "cooldown_ms": self.cooldown_ms,
        }


class InteractionSynthesisEngine:
    _instance: Optional["InteractionSynthesisEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "InteractionSynthesisEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._networks: Dict[str, InteractionNetwork] = {}
        self._profiles: Dict[str, ProgressionProfile] = {}
        self._conflicts: List[ConflictReport] = []
        self._feedback_specs: Dict[str, List[FeedbackSpec]] = {}
        self._total_syntheses: int = 0
        self._total_conflicts_detected: int = 0

        self._domain_knowledge: Dict[str, Dict[str, Any]] = {
            "movement": {
                "primitives": ["walk", "run", "jump", "dash", "slide", "wall_jump", "double_jump", "glide", "teleport"],
                "physics_keys": ["speed", "acceleration", "gravity_scale", "jump_force", "friction", "air_control"],
                "common_inputs": ["stick", "dpad", "button_a", "trigger_l", "trigger_r"],
            },
            "combat": {
                "primitives": ["light_attack", "heavy_attack", "block", "parry", "dodge", "special", "ultimate", "combo"],
                "physics_keys": ["damage", "knockback", "hitstun", "range", "attack_speed", "armor"],
                "common_inputs": ["button_x", "button_y", "button_b", "trigger_r", "bumper_l"],
            },
            "puzzle": {
                "primitives": ["push", "pull", "rotate", "activate", "connect", "sequence", "match", "sort"],
                "physics_keys": ["weight", "friction", "magnetism", "conductivity", "mass"],
                "common_inputs": ["touch", "drag", "click", "swipe", "hold"],
            },
            "social": {
                "primitives": ["talk", "trade", "gift", "recruit", "command", "persuade", "intimidate", "befriend"],
                "physics_keys": ["reputation", "relationship", "charisma", "alignment", "trust"],
                "common_inputs": ["button_a", "dpad", "menu_select", "dialog_option"],
            },
            "exploration": {
                "primitives": ["scan", "examine", "collect", "climb", "swim", "dig", "open", "map"],
                "physics_keys": ["vision_range", "interaction_radius", "carry_capacity", "climb_speed"],
                "common_inputs": ["button_x", "stick_click", "trigger_l", "touch_hold"],
            },
            "resource": {
                "primitives": ["gather", "craft", "build", "trade", "store", "consume", "upgrade", "salvage"],
                "physics_keys": ["carry_weight", "craft_speed", "storage_capacity", "resource_yield"],
                "common_inputs": ["button_x", "hold_button", "menu_navigate", "quick_slot"],
            },
            "building": {
                "primitives": ["place", "rotate", "snap", "demolish", "paint", "resize", "blueprint", "terraform"],
                "physics_keys": ["grid_size", "snap_distance", "placement_range", "structural_integrity"],
                "common_inputs": ["mouse", "scroll_wheel", "button_a", "button_b", "modifier_key"],
            },
            "stealth": {
                "primitives": ["crouch", "cover", "distract", "sneak", "hide_body", "lockpick", "disguise", "silent_takedown"],
                "physics_keys": ["noise_radius", "vision_cone", "detection_speed", "cover_effectiveness"],
                "common_inputs": ["button_b", "stick", "trigger_l", "hold_button", "quick_press"],
            },
        }

    def synthesize_interaction_network(
        self,
        description: str,
        domains: Optional[List[str]] = None,
        interaction_count: int = 8,
        complexity_target: float = 0.6,
    ) -> InteractionNetwork:
        domain_list = domains or ["movement", "combat"]
        domain_list = [d for d in domain_list if d in self._domain_knowledge]

        interactions: List[InteractionConcept] = []
        for idx in range(interaction_count):
            domain_idx = idx % len(domain_list)
            domain_name = domain_list[domain_idx]
            domain_info = self._domain_knowledge.get(domain_name, {})

            primitives = domain_info.get("primitives", ["interact"])
            physics_keys = domain_info.get("physics_keys", [])
            common_inputs = domain_info.get("common_inputs", ["button_a"])

            primitive = primitives[idx % len(primitives)]
            physics = {}
            for k in physics_keys:
                physics[k] = round(0.3 + (idx / interaction_count) * 0.6, 2)

            concept = InteractionConcept(
                name=f"{domain_name}_{primitive}",
                domain=InteractionDomain(domain_name),
                description=f"{description} — {primitive} interaction in {domain_name} domain",
                primary_action=primitive,
                input_binding=common_inputs[idx % len(common_inputs)],
                physics_properties=physics,
                prerequisite_interactions=[],
                feedback_channels=[FeedbackChannel.VISUAL, FeedbackChannel.AUDIO],
                cooldown_ms=100 + idx * 50,
                energy_cost=round(0.1 + idx * 0.05, 2),
                complexity_rating=round(complexity_target * (0.7 + idx * 0.05), 2),
                synergy_tags=[domain_name, primitive],
            )
            interactions.append(concept)

        adjacency: Dict[str, List[str]] = {}
        for i, c in enumerate(interactions):
            neighbors = []
            if i > 0:
                neighbors.append(interactions[i - 1].id)
            if i < len(interactions) - 1:
                neighbors.append(interactions[i + 1].id)
            adjacency[c.id] = neighbors

        entry_points = [interactions[0].id]
        if len(interactions) > interaction_count // 2:
            entry_points.append(interactions[interaction_count // 2].id)

        density = min(1.0, len(adjacency) / max(1, interaction_count * 2))

        network = InteractionNetwork(
            name=f"Synthesis: {description[:40]}",
            interactions=interactions,
            adjacency_map=adjacency,
            entry_points=entry_points,
            network_density=round(density, 3),
            overall_complexity=round(complexity_target, 3),
            cohesion_score=round(0.5 + (density * 0.3), 3),
        )

        self._networks[network.id] = network
        self._total_syntheses += 1
        return network

    def compute_progression_curve(
        self,
        interaction_id: str,
        scaling_type: str = "linear",
        initial_difficulty: float = 0.3,
        final_difficulty: float = 0.9,
        step_count: int = 10,
    ) -> ProgressionProfile:
        thresholds = []
        for s in range(step_count):
            t = s / (step_count - 1) if step_count > 1 else 0
            if scaling_type == "exponential":
                value = initial_difficulty + (final_difficulty - initial_difficulty) * (t ** 2)
            elif scaling_type == "logarithmic":
                value = initial_difficulty + (final_difficulty - initial_difficulty) * (t ** 0.5)
            elif scaling_type == "sigmoid":
                midpoint = 0.5
                steepness = 6.0
                sigmoid = 1.0 / (1.0 + 2.71828 ** (-steepness * (t - midpoint)))
                value = initial_difficulty + (final_difficulty - initial_difficulty) * sigmoid
            else:
                value = initial_difficulty + (final_difficulty - initial_difficulty) * t
            thresholds.append(round(value, 4))

        profile = ProgressionProfile(
            interaction_id=interaction_id,
            scaling_curve=scaling_type,
            initial_difficulty=initial_difficulty,
            final_difficulty=final_difficulty,
            scaling_factors={
                "speed_multiplier": round(1.0 + (final_difficulty - initial_difficulty) * 0.5, 2),
                "accuracy_required": round(0.5 + final_difficulty * 0.5, 2),
                "reaction_window_ms": round(500 - final_difficulty * 300),
            },
            unlock_conditions={"player_level": step_count, "previous_mastery": 0.8},
            mastery_thresholds=thresholds,
        )

        self._profiles[profile.id] = profile
        return profile

    def detect_interaction_conflicts(
        self,
        network_id: str,
        tolerance: float = 0.4,
    ) -> List[ConflictReport]:
        network = self._networks.get(network_id)
        if not network:
            return []

        reports: List[ConflictReport] = []
        interactions = network.interactions

        for i, ia in enumerate(interactions):
            for j, ib in enumerate(interactions):
                if j <= i:
                    continue

                domain_overlap = 1.0 if ia.domain == ib.domain else 0.0
                input_conflict = ia.input_binding == ib.input_binding
                timing_conflict = abs(ia.cooldown_ms - ib.cooldown_ms) < 50

                if input_conflict and domain_overlap > tolerance:
                    severity = ConflictSeverity.CRITICAL if timing_conflict else ConflictSeverity.HIGH
                    report = ConflictReport(
                        interaction_a=ia.id,
                        interaction_b=ib.id,
                        severity=severity,
                        description=f"Input conflict between {ia.name} and {ib.name} sharing '{ia.input_binding}'",
                        suggested_resolution=f"Remap {ib.name} to a different input or add context-based filtering",
                        domain_overlap=domain_overlap,
                        input_conflict=True,
                        timing_conflict=timing_conflict,
                    )
                elif timing_conflict and domain_overlap > tolerance:
                    report = ConflictReport(
                        interaction_a=ia.id,
                        interaction_b=ib.id,
                        severity=ConflictSeverity.MEDIUM,
                        description=f"Timing overlap between {ia.name} and {ib.name}",
                        suggested_resolution=f"Add cooldown staggering or priority resolution",
                        domain_overlap=domain_overlap,
                        timing_conflict=True,
                    )
                else:
                    continue

                reports.append(report)
                self._total_conflicts_detected += 1

        self._conflicts.extend(reports)
        return reports

    def generate_feedback_spec(
        self,
        interaction_id: str,
        channels: Optional[List[str]] = None,
        intensity: float = 0.7,
    ) -> List[FeedbackSpec]:
        channel_enums = []
        if channels:
            for ch in channels:
                try:
                    channel_enums.append(FeedbackChannel(ch))
                except ValueError:
                    channel_enums.append(FeedbackChannel.VISUAL)
        else:
            channel_enums = [FeedbackChannel.VISUAL, FeedbackChannel.AUDIO, FeedbackChannel.UI]

        specs = []
        for ch in channel_enums:
            spec = FeedbackSpec(
                interaction_id=interaction_id,
                channel=ch,
                trigger_event="on_interaction_execute",
                duration_ms=300 if ch == FeedbackChannel.VISUAL else 200,
                intensity=round(intensity * (0.8 if ch == FeedbackChannel.UI else 1.0), 2),
                parameters={
                    "easing": "ease_out_cubic",
                    "blend_mode": "additive" if ch == FeedbackChannel.VISUAL else "normal",
                    "volume": round(intensity * 0.8, 2) if ch == FeedbackChannel.AUDIO else 0.5,
                },
            )
            specs.append(spec)

        if interaction_id not in self._feedback_specs:
            self._feedback_specs[interaction_id] = []
        self._feedback_specs[interaction_id].extend(specs)

        return specs

    def validate_loop_integrity(
        self,
        network_id: str,
    ) -> Dict[str, Any]:
        network = self._networks.get(network_id)
        if not network:
            return {"valid": False, "error": "Network not found"}

        issues: List[str] = []
        warnings: List[str] = []

        if not network.entry_points:
            issues.append("No entry points defined — player has no starting interaction")

        visited: set = set()
        def dfs(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            for neighbor in network.adjacency_map.get(node_id, []):
                dfs(neighbor)

        for ep in network.entry_points:
            dfs(ep)

        unreachable = [i.id for i in network.interactions if i.id not in visited]
        if unreachable:
            warnings.append(f"{len(unreachable)} interactions are unreachable from entry points")

        if network.network_density < 0.1:
            warnings.append("Network density is very low — interactions are too isolated")
        elif network.network_density > 0.9:
            warnings.append("Network density is very high — may cause overwhelming complexity")

        if network.cohesion_score < 0.3:
            warnings.append("Low cohesion score — interactions may feel disconnected")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "reachable_count": len(visited),
            "total_interactions": len(network.interactions),
            "entry_points": network.entry_points,
            "network_density": network.network_density,
            "cohesion_score": network.cohesion_score,
        }

    def get_network(self, network_id: str) -> Optional[InteractionNetwork]:
        return self._networks.get(network_id)

    def list_networks(self) -> List[Dict[str, Any]]:
        return [
            {"id": n.id, "name": n.name, "interaction_count": len(n.interactions),
             "density": n.network_density, "cohesion": n.cohesion_score}
            for n in self._networks.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_syntheses": self._total_syntheses,
            "total_networks": len(self._networks),
            "total_interactions": sum(len(n.interactions) for n in self._networks.values()),
            "total_profiles": len(self._profiles),
            "total_conflicts_detected": self._total_conflicts_detected,
            "total_feedback_specs": sum(len(specs) for specs in self._feedback_specs.values()),
            "domain_coverage": len(self._domain_knowledge),
        }


def get_interaction_synthesis_engine() -> InteractionSynthesisEngine:
    return InteractionSynthesisEngine()