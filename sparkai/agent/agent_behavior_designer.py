"""
SparkLabs Agent - Behavior Designer

AI behavior pattern designer and behavior profile generator for
game NPCs and autonomous agents. Defines personality-driven
behavior profiles, state transitions between behavior patterns,
and generates executable behavior scripts from declarative
profiles.

Architecture:
  BehaviorDesigner
    |-- Profile Manager (create, query, clone behavior profiles)
    |-- Transition Graph (pattern-to-pattern trigger mappings)
    |-- Script Generator (profile-to-executable code generation)
    |-- Behavior Simulator (predictive behavior trace simulation)
    |-- Coherence Evaluator (behavioral consistency validation)

Behavior Patterns:
  - PATROL, CHASE, FLEE, AMBUSH, GUARD, WANDER,
    SEARCH, COOPERATE, RETREAT, BERSERK

Decision Models:
  - STATE_MACHINE: finite state-based transitions
  - UTILITY_AI: scored action selection with utility curves
  - GOAL_ORIENTED: goal-driven action planning (GOAP)
  - HTN_PLANNER: hierarchical task network decomposition
  - REINFORCEMENT: learned policy via reward feedback
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class BehaviorPattern(Enum):
    PATROL = auto()
    CHASE = auto()
    FLEE = auto()
    AMBUSH = auto()
    GUARD = auto()
    WANDER = auto()
    SEARCH = auto()
    COOPERATE = auto()
    RETREAT = auto()
    BERSERK = auto()


class PersonalityTrait(Enum):
    AGGRESSIVE = auto()
    DEFENSIVE = auto()
    CURIOUS = auto()
    CAUTIOUS = auto()
    SOCIAL = auto()
    SOLITARY = auto()
    TERRITORIAL = auto()
    PEACEFUL = auto()


class DecisionModel(Enum):
    STATE_MACHINE = auto()
    UTILITY_AI = auto()
    GOAL_ORIENTED = auto()
    HTN_PLANNER = auto()
    REINFORCEMENT = auto()


@dataclass
class BehaviorProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    entity_type: str = ""
    personality_traits: List[PersonalityTrait] = field(default_factory=list)
    default_pattern: BehaviorPattern = BehaviorPattern.PATROL
    decision_model: DecisionModel = DecisionModel.STATE_MACHINE
    aggression_level: float = 0.5
    cooperation_level: float = 0.5
    curiosity_level: float = 0.5
    flee_threshold: float = 0.3
    perception_radius: float = 10.0
    memory_span_seconds: float = 30.0
    home_position_x: float = 0.0
    home_position_y: float = 0.0
    home_position_z: float = 0.0

    def validate(self) -> List[str]:
        issues: List[str] = []
        fields_to_check: List[Tuple[str, float]] = [
            ("aggression_level", self.aggression_level),
            ("cooperation_level", self.cooperation_level),
            ("curiosity_level", self.curiosity_level),
            ("flee_threshold", self.flee_threshold),
        ]
        for name, value in fields_to_check:
            if not 0.0 <= value <= 1.0:
                issues.append(f"{name} must be between 0.0 and 1.0, got {value}")
        if self.perception_radius <= 0:
            issues.append("perception_radius must be positive")
        if self.memory_span_seconds < 0:
            issues.append("memory_span_seconds must be non-negative")
        if not self.name.strip():
            issues.append("name is required")
        return issues

    def has_trait(self, trait: PersonalityTrait) -> bool:
        return trait in self.personality_traits

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "personality_traits": [t.name for t in self.personality_traits],
            "default_pattern": self.default_pattern.name,
            "decision_model": self.decision_model.name,
            "aggression_level": self.aggression_level,
            "cooperation_level": self.cooperation_level,
            "curiosity_level": self.curiosity_level,
            "flee_threshold": self.flee_threshold,
            "perception_radius": self.perception_radius,
            "memory_span_seconds": self.memory_span_seconds,
            "home_position": (self.home_position_x, self.home_position_y, self.home_position_z),
        }


@dataclass
class BehaviorTransition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_pattern: BehaviorPattern = BehaviorPattern.PATROL
    to_pattern: BehaviorPattern = BehaviorPattern.PATROL
    trigger_condition: str = ""
    priority: int = 0
    cooldown_seconds: float = 1.0
    probability: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_pattern": self.from_pattern.name,
            "to_pattern": self.to_pattern.name,
            "trigger_condition": self.trigger_condition,
            "priority": self.priority,
            "cooldown_seconds": self.cooldown_seconds,
            "probability": self.probability,
        }


class BehaviorDesigner:
    _instance: Optional["BehaviorDesigner"] = None

    # Trigger condition templates keyed by (from, to) pattern pair
    _TRIGGER_TEMPLATES: Dict[Tuple[BehaviorPattern, BehaviorPattern], str] = {
        (BehaviorPattern.PATROL, BehaviorPattern.CHASE): "target_spotted_in_range",
        (BehaviorPattern.PATROL, BehaviorPattern.FLEE): "health_below_threshold",
        (BehaviorPattern.CHASE, BehaviorPattern.BERSERK): "target_in_attack_range",
        (BehaviorPattern.GUARD, BehaviorPattern.CHASE): "intruder_detected",
        (BehaviorPattern.WANDER, BehaviorPattern.SEARCH): "stimulus_heard",
        (BehaviorPattern.CHASE, BehaviorPattern.RETREAT): "reinforcements_lost",
        (BehaviorPattern.RETREAT, BehaviorPattern.GUARD): "reached_safe_position",
    }

    _DECISION_SCRIPTS: Dict[DecisionModel, str] = {
        DecisionModel.STATE_MACHINE: "fsm_controller",
        DecisionModel.UTILITY_AI: "utility_scorer",
        DecisionModel.GOAL_ORIENTED: "goap_planner",
        DecisionModel.HTN_PLANNER: "htn_decomposer",
        DecisionModel.REINFORCEMENT: "rl_policy_network",
    }

    def __init__(self):
        self._profiles: Dict[str, BehaviorProfile] = {}
        self._transitions: Dict[str, List[BehaviorTransition]] = {}
        self._profile_count: int = 0
        self._transition_count: int = 0

    @classmethod
    def get_instance(cls) -> "BehaviorDesigner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_profile(
        self,
        name: str,
        entity_type: str,
        traits: List[PersonalityTrait],
        default_pattern: BehaviorPattern,
    ) -> BehaviorProfile:
        profile = BehaviorProfile(
            name=name,
            entity_type=entity_type,
            personality_traits=traits,
            default_pattern=default_pattern,
        )
        self._profiles[profile.id] = profile
        self._transitions[profile.id] = []
        self._profile_count += 1
        return profile

    def add_transition(
        self,
        profile_id: str,
        from_pattern: BehaviorPattern,
        to_pattern: BehaviorPattern,
        trigger: str,
        priority: int = 0,
        cooldown: float = 1.0,
        probability: float = 1.0,
    ) -> str:
        if profile_id not in self._profiles:
            return ""

        transition = BehaviorTransition(
            from_pattern=from_pattern,
            to_pattern=to_pattern,
            trigger_condition=trigger,
            priority=priority,
            cooldown_seconds=cooldown,
            probability=probability,
        )
        if profile_id not in self._transitions:
            self._transitions[profile_id] = []
        self._transitions[profile_id].append(transition)
        self._transition_count += 1
        return transition.id

    def generate_behavior_script(self, profile_id: str) -> str:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return ""

        lines: List[str] = []
        lines.append(f"# Behavior Script: {profile.name}")
        lines.append(f"# Entity Type: {profile.entity_type}")
        lines.append(f"# Decision Model: {profile.decision_model.name}")
        lines.append(f"# Default Pattern: {profile.default_pattern.name}")
        lines.append("")

        lines.append("## Personality Configuration")
        for trait in profile.personality_traits:
            lines.append(f"trait: {trait.name.lower()}")
        lines.append(f"aggression: {profile.aggression_level}")
        lines.append(f"cooperation: {profile.cooperation_level}")
        lines.append(f"curiosity: {profile.curiosity_level}")
        lines.append(f"flee_threshold: {profile.flee_threshold}")
        lines.append(f"perception_radius: {profile.perception_radius}")
        lines.append(f"memory_span: {profile.memory_span_seconds}s")
        lines.append("")

        transitions = self._transitions.get(profile_id, [])
        if transitions:
            lines.append("## Transition Rules")
            sorted_transitions = sorted(transitions, key=lambda t: t.priority, reverse=True)
            for t in sorted_transitions:
                lines.append(
                    f"{t.from_pattern.name} -> {t.to_pattern.name}"
                    f" : {t.trigger_condition}"
                    f" [priority={t.priority}, cooldown={t.cooldown_seconds}s, p={t.probability}]"
                )
        else:
            lines.append("## Transition Rules")
            lines.append("# Using default pattern transitions based on personality")

        lines.append("")
        lines.append("## Decision Pipeline")
        dm = profile.decision_model
        if dm == DecisionModel.STATE_MACHINE:
            lines.append(f"init_state: {profile.default_pattern.name}")
            lines.append("evaluate: check_transitions(current_state, context)")
        elif dm == DecisionModel.UTILITY_AI:
            lines.append("evaluate: score_all_actions(context)")
            lines.append("select: argmax(utility_scores)")
        elif dm == DecisionModel.GOAL_ORIENTED:
            lines.append("plan: build_action_sequence(goal, world_state)")
            lines.append("execute: step_plan(plan_stack)")
        elif dm == DecisionModel.HTN_PLANNER:
            lines.append("decompose: expand_task(root_task, world_state)")
            lines.append("execute: process_primitive_tasks(task_queue)")
        elif dm == DecisionModel.REINFORCEMENT:
            lines.append("observe: encode_state_sensor_data()")
            lines.append("act: policy_network.predict(observation)")

        return "\n".join(lines)

    def simulate_behavior(
        self,
        profile_id: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return []

        transitions = self._transitions.get(profile_id, [])
        trace: List[Dict[str, Any]] = []
        current_pattern = profile.default_pattern
        steps = context.get("steps", 10)

        for step in range(steps):
            available = [
                t for t in transitions
                if t.from_pattern == current_pattern
            ]
            if available:
                chosen = max(available, key=lambda t: t.priority)
                next_pattern = chosen.to_pattern
            else:
                next_pattern = current_pattern

            trace.append({
                "step": step,
                "from_pattern": current_pattern.name,
                "to_pattern": next_pattern.name,
                "trigger": chosen.trigger_condition if available else "none",
            })
            current_pattern = next_pattern

        return trace

    def evaluate_behavior_coherence(self, profile_id: str) -> Dict[str, Any]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {"error": "profile not found"}

        transitions = self._transitions.get(profile_id, [])
        issues: List[str] = []

        validation_issues = profile.validate()
        issues.extend(validation_issues)

        from_patterns = {t.from_pattern for t in transitions}
        to_patterns = {t.to_pattern for t in transitions}

        if profile.default_pattern not in from_patterns and transitions:
            issues.append(
                f"default_pattern {profile.default_pattern.name} has no outgoing transitions"
            )

        has_recovery = any(
            t.to_pattern == profile.default_pattern for t in transitions
        )
        if transitions and not has_recovery:
            issues.append("no transition leads back to the default pattern")

        pattern_count = len(from_patterns | to_patterns)
        transition_count = len(transitions)
        density = transition_count / max(pattern_count, 1)

        return {
            "profile_id": profile_id,
            "profile_name": profile.name,
            "is_coherent": len(issues) == 0,
            "issues": issues,
            "issue_count": len(issues),
            "transition_count": transition_count,
            "pattern_count": pattern_count,
            "graph_density": round(density, 2),
            "coherence_score": round(max(0.0, 1.0 - (len(issues) * 0.2)), 2),
        }

    def clone_profile(self, profile_id: str, new_name: str) -> Optional[BehaviorProfile]:
        original = self._profiles.get(profile_id)
        if original is None:
            return None

        cloned = BehaviorProfile(
            name=new_name,
            entity_type=original.entity_type,
            personality_traits=list(original.personality_traits),
            default_pattern=original.default_pattern,
            decision_model=original.decision_model,
            aggression_level=original.aggression_level,
            cooperation_level=original.cooperation_level,
            curiosity_level=original.curiosity_level,
            flee_threshold=original.flee_threshold,
            perception_radius=original.perception_radius,
            memory_span_seconds=original.memory_span_seconds,
            home_position_x=original.home_position_x,
            home_position_y=original.home_position_y,
            home_position_z=original.home_position_z,
        )
        self._profiles[cloned.id] = cloned

        original_transitions = self._transitions.get(profile_id, [])
        cloned_transitions = [
            BehaviorTransition(
                from_pattern=t.from_pattern,
                to_pattern=t.to_pattern,
                trigger_condition=t.trigger_condition,
                priority=t.priority,
                cooldown_seconds=t.cooldown_seconds,
                probability=t.probability,
            )
            for t in original_transitions
        ]
        self._transitions[cloned.id] = cloned_transitions
        self._profile_count += 1
        self._transition_count += len(cloned_transitions)

        return cloned

    def get_stats(self) -> Dict[str, Any]:
        total_transitions = sum(len(ts) for ts in self._transitions.values())
        model_counts: Dict[str, int] = {}
        pattern_counts: Dict[str, int] = {}
        trait_counts: Dict[str, int] = {}

        for profile in self._profiles.values():
            model_key = profile.decision_model.name
            model_counts[model_key] = model_counts.get(model_key, 0) + 1

            pattern_key = profile.default_pattern.name
            pattern_counts[pattern_key] = pattern_counts.get(pattern_key, 0) + 1

            for trait in profile.personality_traits:
                trait_key = trait.name
                trait_counts[trait_key] = trait_counts.get(trait_key, 0) + 1

        return {
            "total_profiles": len(self._profiles),
            "profiles_created": self._profile_count,
            "total_transitions": total_transitions,
            "transitions_created": self._transition_count,
            "avg_transitions_per_profile": round(
                total_transitions / max(len(self._profiles), 1), 1
            ),
            "models": model_counts,
            "default_patterns": pattern_counts,
            "trait_distribution": trait_counts,
        }


def get_behavior_designer() -> BehaviorDesigner:
    return BehaviorDesigner.get_instance()