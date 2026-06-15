"""
SparkLabs Agent - Game Designer

An autonomous AI game designer that generates complete game designs from
high-level descriptions. Produces comprehensive design documents, mechanics
specifications, progression systems, and game economy models tailored to
different genres for the AI-native game engine.

Core capabilities:
  - Genre-aware design generation with distinct mechanic templates
  - Procedural mechanics specification with complexity scoring
  - Progression system design with multiple curve types
  - Economy system modeling with currency, sink, and source balancing
  - Full end-to-end design pipeline from concept to polished document
  - Design evaluation across feasibility, fun factor, balance, and completeness

Architecture:
  GameDesignerAgent (Singleton)
    |-- DesignDocument (dataclass)
    |-- MechanicSpec (dataclass)
    |-- ProgressionSystem (dataclass)
    |-- EconomySystem (dataclass)
    |-- create_design()
    |-- define_mechanics()
    |-- design_progression()
    |-- design_economy()
    |-- evaluate_design()
    |-- generate_full_design()
    |-- list_designs()
    |-- get_stats()

Usage:
    designer = get_game_designer()
    doc = designer.generate_full_design("Star Vault", GameGenre.METROIDVANIA,
        "A cosmic horror metroidvania set aboard a derelict space station")
    mechanics = designer.define_mechanics(doc.doc_id, count=6)
    prog = designer.design_progression(doc.doc_id, levels_count=30)
    economy = designer.design_economy(doc.doc_id)
    evaluation = designer.evaluate_design(doc.doc_id)
"""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


# =============================================================================
# Enums
# =============================================================================

class GameGenre(Enum):
    PLATFORMER = "platformer"
    RPG = "rpg"
    STRATEGY = "strategy"
    PUZZLE = "puzzle"
    SHOOTER = "shooter"
    RACING = "racing"
    SIMULATION = "simulation"
    ADVENTURE = "adventure"
    FIGHTING = "fighting"
    ROGUELIKE = "roguelike"
    METROIDVANIA = "metroidvania"
    SURVIVAL = "survival"
    HORROR = "horror"
    VISUAL_NOVEL = "visual_novel"
    SANDBOX = "sandbox"


class DesignPhase(Enum):
    CONCEPT = "concept"
    MECHANICS = "mechanics"
    SYSTEMS = "systems"
    PROGRESSION = "progression"
    ECONOMY = "economy"
    NARRATIVE = "narrative"
    LEVELS = "levels"
    POLISH = "polish"


class TargetPlatform(Enum):
    MOBILE = "mobile"
    WEB = "web"
    DESKTOP = "desktop"
    CONSOLE = "console"
    VR = "vr"
    CROSS_PLATFORM = "cross_platform"


class ProgressionCurveType(Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    STEPPED = "stepped"
    SIGMOID = "sigmoid"


class MechanicCategory(Enum):
    MOVEMENT = "movement"
    COMBAT = "combat"
    INTERACTION = "interaction"
    RESOURCE = "resource"
    PROGRESSION = "progression"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    CRAFTING = "crafting"


# =============================================================================
# Genre-Specific Procedural Data
# =============================================================================

_GENRE_MECHANIC_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "platformer": [
        {"name": "Precision Jump", "category": "movement",
         "desc": "Variable-height jump with air control for precise platform navigation",
         "params": {"jump_height": 3.0, "air_control": 0.7, "coyote_time_ms": 120}},
        {"name": "Wall Slide", "category": "movement",
         "desc": "Slide down vertical surfaces with controllable descent speed",
         "params": {"slide_speed": 2.5, "friction": 0.3, "max_slide_duration": 4.0}},
        {"name": "Dash Burst", "category": "movement",
         "desc": "Short-range horizontal burst that crosses gaps and evades hazards",
         "params": {"dash_distance": 4.0, "dash_cooldown": 0.8, "invincibility_frames": 6}},
        {"name": "Hazard Cycle", "category": "interaction",
         "desc": "Timed environmental hazards that create rhythm-based challenge windows",
         "params": {"cycle_period": 3.0, "safe_window": 1.2, "damage_on_contact": 1}},
        {"name": "Collectible Trail", "category": "resource",
         "desc": "Scattered collectibles that guide player movement and reward exploration",
         "params": {"collectible_value": 10, "trail_density": 0.6, "bonus_threshold": 50}},
        {"name": "Momentum Chain", "category": "movement",
         "desc": "Consecutive actions build speed multiplier, rewarding fluid execution",
         "params": {"chain_window": 1.5, "max_multiplier": 3.0, "decay_rate": 0.8}},
    ],
    "rpg": [
        {"name": "Skill Branching", "category": "progression",
         "desc": "Multi-path skill tree with mutually exclusive specialization branches",
         "params": {"branches": 3, "nodes_per_branch": 8, "respec_cost": 500}},
        {"name": "Party Synergy", "category": "combat",
         "desc": "Combo abilities triggered when party members fulfill positional conditions",
         "params": {"max_combo_chain": 4, "synergy_bonus": 0.25, "trigger_range": 3.0}},
        {"name": "Dialogue Persuasion", "category": "social",
         "desc": "Stat-gated dialogue options that unlock alternate quest resolutions",
         "params": {"stat_thresholds": [10, 20, 35], "failure_penalty": "reputation_loss"}},
        {"name": "Equipment Affinity", "category": "progression",
         "desc": "Weapons and armor gain bonus stats based on usage history with the character",
         "params": {"affinity_max": 100, "bonus_per_10_affinity": 0.03, "decay_on_unequip": 5}},
        {"name": "Elemental Rock-Paper-Scissors", "category": "combat",
         "desc": "Six-element wheel where each element counters and is countered by two others",
         "params": {"elements": ["fire", "water", "earth", "air", "light", "dark"],
                    "counter_multiplier": 1.5, "resist_multiplier": 0.5}},
        {"name": "World State Flags", "category": "interaction",
         "desc": "Persistent binary flags set by player decisions that alter world content",
         "params": {"max_flags": 64, "flag_categories": ["moral", "political", "personal"]}},
    ],
    "strategy": [
        {"name": "Fog of War", "category": "exploration",
         "desc": "Line-of-sight based vision system with unit-specific sight ranges",
         "params": {"base_sight_range": 6, "terrain_modifiers": True, "reveal_duration": 3}},
        {"name": "Tech Tree Unlock", "category": "progression",
         "desc": "Directed acyclic graph of research nodes with prerequisite dependencies",
         "params": {"total_nodes": 40, "starting_nodes": 3, "research_time_base": 60}},
        {"name": "Supply Line", "category": "resource",
         "desc": "Units require connection to production buildings to maintain effectiveness",
         "params": {"max_supply_range": 8, "supply_decay_rate": 0.1, "cutoff_penalty": 0.5}},
        {"name": "Terrain Tactics", "category": "combat",
         "desc": "Tile-based combat modifiers for elevation, cover, and choke points",
         "params": {"high_ground_bonus": 0.25, "cover_reduction": 0.4, "choke_limit": 2}},
        {"name": "Resource Node Control", "category": "resource",
         "desc": "Contestable map points that generate passive income when controlled",
         "params": {"node_types": ["minerals", "energy", "research"],
                    "income_interval": 30, "contested_decay": 0.5}},
        {"name": "Formation Bonus", "category": "combat",
         "desc": "Adjacent unit arrangement grants stat bonuses based on formation shape",
         "params": {"formations": ["line", "wedge", "square", "diamond"],
                    "max_bonus": 0.3, "flank_penalty": 0.4}},
    ],
    "puzzle": [
        {"name": "Constraint Propagation", "category": "interaction",
         "desc": "Solving one sub-puzzle reveals constraints for others in a dependency chain",
         "params": {"max_chain_depth": 5, "hint_delay_seconds": 45, "auto_propagate": True}},
        {"name": "State Inversion", "category": "interaction",
         "desc": "Toggle mechanic that flips binary states of connected puzzle elements",
         "params": {"max_connections": 4, "toggle_cooldown": 0.3, "undo_limit": 10}},
        {"name": "Color Mixing Grid", "category": "interaction",
         "desc": "Combine primary colors on a grid to match target patterns through additive mixing",
         "params": {"base_colors": ["red", "blue", "yellow"], "secondary_colors": ["green", "purple", "orange"],
                    "grid_size": [4, 6, 8]}},
        {"name": "Path Routing", "category": "interaction",
         "desc": "Draw continuous paths through nodes under constraints of single-visit and direction locks",
         "params": {"min_nodes": 4, "max_nodes": 12, "direction_locks": ["up", "down", "left", "right"]}},
        {"name": "Physics Stacking", "category": "interaction",
         "desc": "Stack objects with different physical properties to reach target heights",
         "params": {"object_types": ["box", "ball", "plank", "spring"],
                    "gravity": 9.8, "stack_stability_threshold": 0.6}},
        {"name": "Sequential Trigger", "category": "interaction",
         "desc": "Activate triggers in correct order, where each trigger modifies the state of others",
         "params": {"trigger_count": 4, "order_memory": True, "reset_on_error": False}},
    ],
    "shooter": [
        {"name": "Recoil Pattern", "category": "combat",
         "desc": "Predictable weapon-specific recoil spread that rewards learned compensation",
         "params": {"vertical_recoil": 0.8, "horizontal_variance": 0.3, "recovery_speed": 0.5}},
        {"name": "Cover System", "category": "movement",
         "desc": "Contextual snap-to-cover with blind-fire and pop-out shooting options",
         "params": {"cover_height": [0.5, 1.0], "exposure_time": 0.4, "blind_fire_accuracy": 0.3}},
        {"name": "Ammo Economy", "category": "resource",
         "desc": "Limited ammunition pool with weapon-specific pickups and reserve management",
         "params": {"ammo_types": ["light", "heavy", "special", "explosive"],
                    "max_reserve_per_type": [200, 80, 20, 6]}},
        {"name": "Weapon Loadout", "category": "progression",
         "desc": "Two-weapon carry limit with strategic pre-mission selection and field swapping",
         "params": {"carry_slots": 2, "swap_time": 0.8, "weapon_categories": ["primary", "sidearm", "heavy"]}},
        {"name": "Hit-Scan vs Projectile", "category": "combat",
         "desc": "Weapons use either instant hit-scan or traveling projectiles with travel time",
         "params": {"projectile_speed_range": [30, 120], "hit_scan_falloff_start": 20, "falloff_end": 50}},
        {"name": "Killstreak Reward", "category": "progression",
         "desc": "Consecutive eliminations without death grant escalating temporary power-ups",
         "params": {"streak_thresholds": [3, 5, 7, 10],
                    "rewards": ["radar_pulse", "damage_boost", "airstrike", "reveal_all"]}},
    ],
    "racing": [
        {"name": "Drift Boost", "category": "movement",
         "desc": "Sustained drift builds boost gauge; straightening out releases speed burst",
         "params": {"drift_angle_min": 15, "boost_per_second": 8, "max_boost_gauge": 100}},
        {"name": "Slipstream Draft", "category": "movement",
         "desc": "Following closely behind another racer reduces drag and builds speed advantage",
         "params": {"draft_range": 4.0, "draft_speed_bonus": 0.15, "draft_boost_accumulation": 5}},
        {"name": "Vehicle Tuning", "category": "progression",
         "desc": "Adjustable parameters for suspension, gear ratios, tire pressure, and downforce",
         "params": {"tuning_slots": 6, "param_range_per_slot": [0.5, 2.0], "track_specificity": True}},
        {"name": "Rubber-Band AI", "category": "interaction",
         "desc": "Dynamic AI difficulty that compresses the field to maintain competitive tension",
         "params": {"max_speed_boost_pct": 0.12, "min_spread_distance": 3,
                    "compression_frequency": 5}},
        {"name": "Track Hazard", "category": "interaction",
         "desc": "Procedurally placed obstacles and surface changes that alter optimal racing lines",
         "params": {"hazard_types": ["oil", "gravel", "water", "debris"],
                    "hazard_density": 0.15, "grip_reduction": [0.6, 0.3, 0.5, 0.4]}},
        {"name": "Pit Strategy", "category": "resource",
         "desc": "Mandatory pit stops with tire wear and fuel consumption trade-off decisions",
         "params": {"tire_life_laps": [8, 15], "fuel_laps": 20, "pit_time_loss": 18.0}},
    ],
    "simulation": [
        {"name": "Agent Need Hierarchy", "category": "resource",
         "desc": "Simulated agents prioritize actions based on dynamic need satisfaction levels",
         "params": {"needs": ["hunger", "rest", "social", "safety"],
                    "decay_rates": [0.8, 0.5, 0.3, 0.2], "action_priority_threshold": 0.3}},
        {"name": "Supply-Demand Market", "category": "resource",
         "desc": "Autonomous price fluctuation based on aggregate production and consumption rates",
         "params": {"price_elasticity": 1.2, "equilibrium_target": 0.5, "update_interval": 10}},
        {"name": "Day-Night Cycle", "category": "interaction",
         "desc": "Temporal system affecting agent schedules, visibility, and event availability",
         "params": {"cycle_duration_seconds": 600, "phases": ["dawn", "day", "dusk", "night"],
                    "night_visibility_penalty": 0.7}},
        {"name": "Weather Cascade", "category": "interaction",
         "desc": "Markov-chain driven weather system that chains probable weather transitions",
         "params": {"states": ["clear", "cloudy", "rain", "storm", "snow"],
                    "transition_matrix": [[0.6, 0.2, 0.1, 0.05, 0.05],
                                          [0.3, 0.3, 0.2, 0.1, 0.1],
                                          [0.2, 0.2, 0.2, 0.3, 0.1],
                                          [0.3, 0.2, 0.2, 0.2, 0.1],
                                          [0.4, 0.3, 0.1, 0.1, 0.1]]}},
        {"name": "Population Dynamics", "category": "resource",
         "desc": "Birth, death, and migration rates affected by city happiness and resource availability",
         "params": {"base_birth_rate": 0.01, "base_death_rate": 0.008, "migration_factor": 0.5}},
        {"name": "Infrastructure Grid", "category": "interaction",
         "desc": "Network of power, water, and transport connections with capacity and range limits",
         "params": {"grid_types": ["power", "water", "road"], "max_connection_range": 12,
                    "capacity_per_node": 100, "failure_cascade_chance": 0.05}},
    ],
    "adventure": [
        {"name": "Inventory Combination", "category": "interaction",
         "desc": "Combine inventory items in logical ways to create tools that solve environmental puzzles",
         "params": {"max_combine_depth": 3, "logical_affordances": True, "hint_system_delay": 60}},
        {"name": "Environmental Storytelling", "category": "exploration",
         "desc": "Diegetic clues embedded in the environment that reveal narrative without explicit text",
         "params": {"clue_density": 0.4, "clue_types": ["visual", "audio", "spatial", "temporal"]}},
        {"name": "Branching Dialogue", "category": "social",
         "desc": "Conversation trees with persistent consequence tracking across the entire playthrough",
         "params": {"max_branch_depth": 5, "consequence_tags": ["trust", "knowledge", "favor", "hostility"],
                    "callback_flags": True}},
        {"name": "Map Annotation", "category": "exploration",
         "desc": "Player-driven map marking system that records observations and suspected secrets",
         "params": {"marker_types": ["note", "danger", "treasure", "path", "mystery"],
                    "auto_mark_discoveries": True}},
        {"name": "Tool Progression Gate", "category": "progression",
         "desc": "Newly acquired tools retroactively unlock previously inaccessible areas",
         "params": {"tool_count": 5, "gate_retroactivity": True, "visual_distinction": "color_coded"}},
        {"name": "Character Relationship Web", "category": "social",
         "desc": "Dynamic relationship values between NPCs that shift based on player actions and testimony",
         "params": {"relationship_range": [-100, 100], "gossip_propagation_rate": 0.3,
                    "alliance_threshold": 60, "rivalry_threshold": -40}},
    ],
    "fighting": [
        {"name": "Combo String", "category": "combat",
         "desc": "Chained normal attacks with cancel windows into special moves for extended pressure",
         "params": {"max_combo_length": 12, "cancel_window_frames": 8, "damage_scaling_per_hit": 0.9}},
        {"name": "Frame Data Advantage", "category": "combat",
         "desc": "Every move has startup, active, and recovery frames that determine turn-taking",
         "params": {"startup_range": [3, 30], "active_range": [1, 8], "recovery_range": [5, 35],
                    "on_block_advantage": [-12, 5]}},
        {"name": "Super Meter", "category": "resource",
         "desc": "Buildable meter from dealing and taking damage; spent on powerful super moves",
         "params": {"max_meter": 4, "meter_gain_on_hit": 0.15, "meter_gain_on_block": 0.08,
                    "super_costs": [1, 2, 3]}},
        {"name": "Wake-Up Options", "category": "combat",
         "desc": "Multiple get-up actions from knockdown with different invincibility and recovery properties",
         "params": {"options": ["quick_rise", "back_roll", "delayed", "attack_getup"],
                    "invuln_frames": [0, 5, 0, 3], "recovery_frames": [8, 14, 20, 22]}},
        {"name": "Guard Crush", "category": "combat",
         "desc": "Sustained blocking depletes guard gauge; depletion causes stun state",
         "params": {"guard_gauge_max": 100, "chip_damage_pct": 0.1, "crush_duration": 90,
                    "regen_rate": 2.0, "regen_delay": 60}},
        {"name": "Matchup Knowledge", "category": "interaction",
         "desc": "Character-specific properties create advantaged and disadvantaged matchups",
         "params": {"matchup_advantage_range": [-3, 3], "property_types": ["range", "speed", "damage", "mixup"]}},
    ],
    "roguelike": [
        {"name": "Procedural Floor Layout", "category": "exploration",
         "desc": "Algorithmically generated room-and-corridor floor plans with template stitching",
         "params": {"room_count_range": [8, 16], "branching_factor": 2.5, "secret_room_chance": 0.15}},
        {"name": "Item Synergy Engine", "category": "progression",
         "desc": "Items combine effects multiplicatively; discovering synergies is core to mastery",
         "params": {"max_active_items": 12, "synergy_tag_count": 20, "combo_bonus_base": 0.15}},
        {"name": "Permadeath with Meta-Progression", "category": "progression",
         "desc": "Death resets the run but unlocks permanent upgrades through accumulated currency",
         "params": {"meta_currency_per_run": "souls", "upgrade_tree_size": 25, "run_milestone_bonus": True}},
        {"name": "Risk-Reward Rooms", "category": "interaction",
         "desc": "Optional challenge rooms that offer high rewards but impose temporary debuffs",
         "params": {"room_types": ["curse", "boss_rush", "gamble", "time_trial"],
                    "reward_multiplier": 2.5, "failure_penalty": "item_loss"}},
        {"name": "Run Modifier System", "category": "interaction",
         "desc": "Pre-run toggles that increase difficulty for multiplied rewards",
         "params": {"modifier_count": 8, "difficulty_increment_per_mod": 0.15,
                    "reward_multiplier_per_mod": 0.2}},
        {"name": "Seed-Based Generation", "category": "interaction",
         "desc": "Shareable numeric seeds that deterministically recreate identical run layouts",
         "params": {"seed_length": 10, "generation_algorithm": "pcg_hash", "daily_seed_mode": True}},
    ],
    "metroidvania": [
        {"name": "Ability-Gated Lock", "category": "exploration",
         "desc": "Obstacles that require specific acquired abilities to bypass, structuring the critical path",
         "params": {"lock_types": ["door", "gap", "barrier", "height", "element"],
                    "ability_unlock_order": "partial_sequence", "sequence_break_count": 3}},
        {"name": "Interconnected Map", "category": "exploration",
         "desc": "Non-linear world design with multiple routes between zones and looping shortcuts",
         "params": {"zone_count": 8, "connections_per_zone": [2, 5], "shortcut_unlock_triggers": True}},
        {"name": "Movement Upgrade", "category": "movement",
         "desc": "Permanent movement abilities that expand traversal options and combat mobility",
         "params": {"upgrade_sequence": ["dash", "double_jump", "wall_climb", "glide", "teleport"],
                    "backtracking_incentive": "hidden_collectibles"}},
        {"name": "Map Discovery", "category": "exploration",
         "desc": "Fogged map that reveals through exploration with room-shape outline hints",
         "params": {"reveal_radius": 2, "map_room_count": 120, "completion_percentage_visible": True}},
        {"name": "Boss Ability Echo", "category": "combat",
         "desc": "Defeated bosses grant combat abilities that also serve as environment interaction keys",
         "params": {"boss_count": 6, "echo_abilities": ["charge_shot", "ground_pound", "phase_dash",
                          "energy_beam", "barrier", "time_slow"]}},
        {"name": "Hidden Wall Techniques", "category": "exploration",
         "desc": "Breakable or pass-through walls hinted by subtle visual and audio cues",
         "params": {"wall_density_per_zone": 3, "hint_types": ["crack_visual", "draft_audio", "map_gap"],
                    "false_wall_chance": 0.1}},
    ],
    "survival": [
        {"name": "Vital Stats", "category": "resource",
         "desc": "Hunger, thirst, temperature, and stamina must be managed through resource gathering",
         "params": {"stats": ["hunger", "thirst", "temperature", "stamina"],
                    "decay_rates": [0.4, 0.5, 0.2, 0.6],
                    "critical_threshold": 0.15, "death_threshold": 0.0}},
        {"name": "Base Building", "category": "crafting",
         "desc": "Modular construction system with structural integrity and defensive fortification",
         "params": {"building_materials": ["wood", "stone", "metal", "composite"],
                    "structural_integrity_model": True, "max_build_height": 20}},
        {"name": "Crafting Tier Ladder", "category": "crafting",
         "desc": "Progressive crafting tiers where higher-tier items require lower-tier components",
         "params": {"tiers": 5, "components_per_recipe": [2, 3, 4, 5, 6],
                    "tier_unlock_conditions": ["biome_access", "boss_defeat", "research"]}},
        {"name": "Threat Escalation", "category": "combat",
         "desc": "Enemy difficulty and raid frequency increase with player base development level",
         "params": {"threat_levels": 10, "raid_interval_base": 3, "escalation_trigger": "tech_level",
                    "boss_spawn_chance_per_level": 0.05}},
        {"name": "Biome Adaptation", "category": "resource",
         "desc": "Different biomes require specialized gear and strategies; exposure deals damage",
         "params": {"biomes": ["forest", "desert", "tundra", "swamp", "volcanic"],
                    "adaptation_gear_slots": 3, "exposure_damage_rate": 0.3}},
        {"name": "Resource Renewal", "category": "resource",
         "desc": "Harvested resources regenerate over time; over-harvesting causes permanent depletion",
         "params": {"renewal_interval": 600, "sustainable_yield_pct": 0.6, "depletion_threshold": 0.2}},
    ],
    "horror": [
        {"name": "Sanity Meter", "category": "resource",
         "desc": "Psychological stress gauge that distorts perception and enables entity detection",
         "params": {"max_sanity": 100, "decay_sources": ["darkness", "entity_sight", "isolation"],
                    "low_sanity_effects": ["hallucination", "audio_warp", "control_inversion"]}},
        {"name": "Limited Resources", "category": "resource",
         "desc": "Scarce ammunition, health items, and light sources create constant tension",
         "params": {"resource_types": ["ammo", "medkit", "battery", "matches"],
                    "scarcity_multiplier": 0.3, "no_crafting": True}},
        {"name": "Stealth Movement", "category": "movement",
         "desc": "Crouching, slow-walking, and holding breath reduce detection radius from threats",
         "params": {"movement_states": ["sprint", "walk", "crouch", "crawl"],
                    "detection_radii": [12, 8, 4, 2], "breath_hold_duration": 5.0}},
        {"name": "Pursuit Sequence", "category": "combat",
         "desc": "Scripted and dynamic chase sequences where the player must evade rather than fight",
         "params": {"pursuer_speed": 1.1, "obstacle_interaction": "knock_down",
                    "escape_conditions": ["reach_safe_room", "break_line_of_sight", "timer_expiry"]}},
        {"name": "Environmental Soundscape", "category": "interaction",
         "desc": "Positional audio cues signal threat proximity, direction, and emotional state",
         "params": {"audio_layers": ["ambient", "proximity", "threat", "musical_sting"],
                    "cue_distance_thresholds": [20, 10, 5], "silence_as_tension": True}},
        {"name": "Safe Room", "category": "interaction",
         "desc": "Designated save points that provide temporary relief but cannot be lingered in indefinitely",
         "params": {"safe_duration_limit": 120, "save_resource_cost": 1,
                    "threat_escalation_outside": True, "false_safe_room_chance": 0.05}},
    ],
    "visual_novel": [
        {"name": "Choice Branching", "category": "social",
         "desc": "Decision points that route the narrative through mutually exclusive story paths",
         "params": {"branch_points_per_route": 12, "route_count": 4, "bad_end_threshold": -3,
                    "true_end_conditions": "all_routes_complete"}},
        {"name": "Affection Tracker", "category": "social",
         "desc": "Hidden numeric relationship values with each key character, modified by dialogue choices",
         "params": {"tracked_characters": 5, "affection_range": [-50, 100],
                    "visible_to_player": False, "threshold_events": {75: "confession", 90: "special_scene"}}},
        {"name": "Scene Unlock Flags", "category": "progression",
         "desc": "Binary flags triggered by specific choices that gate access to bonus scenes and CG art",
         "params": {"total_flags": 30, "flag_categories": ["character", "event", "hidden"],
                    "completion_tracker_visible": True}},
        {"name": "Text Pacing Control", "category": "interaction",
         "desc": "Adjustable text speed, auto-advance, and backlog review for reading comfort",
         "params": {"speed_levels": 5, "auto_advance_delay": [0.5, 1.0, 1.5, 2.0, 3.0],
                    "backlog_capacity": 200, "voice_line_skip": True}},
        {"name": "Route Locking", "category": "progression",
         "desc": "First playthrough restricts certain routes; subsequent runs unlock based on prior endings",
         "params": {"initial_routes_available": 2, "unlock_condition": "ending_achieved",
                    "new_game_plus_carries": ["gallery", "music", "flags_for_true_end"]}},
        {"name": "Flowchart System", "category": "interaction",
         "desc": "Visual flowchart showing discovered branches with jump-to-choice-point functionality",
         "params": {"max_nodes": 80, "unvisited_nodes": "dimmed", "jump_cost": "lose_progress_from_jump_point",
                    "completion_percentage": True}},
    ],
    "sandbox": [
        {"name": "Voxel Terrain", "category": "interaction",
         "desc": "Cubic-unit world where every block can be placed, broken, and transformed",
         "params": {"block_types": 120, "world_dimensions": [256, 64, 256],
                    "chunk_size": 16, "generation_algorithm": "perlin_octave"}},
        {"name": "Physics Simulation", "category": "interaction",
         "desc": "Rigid-body physics with gravity, collision, and joint constraints for contraptions",
         "params": {"physics_objects": ["block", "wheel", "hinge", "thruster", "sensor"],
                    "gravity": 9.8, "simulation_rate": 60}},
        {"name": "Emergent Systems", "category": "interaction",
         "desc": "Simple rule-based systems (water flow, fire spread, electricity) that create complex interactions",
         "params": {"systems": ["fluid_dynamics", "fire_propagation", "circuit_logic", "plant_growth"],
                    "interaction_matrix": "full_cross_system", "tick_rate": 20}},
        {"name": "Player-Defined Goals", "category": "interaction",
         "desc": "No mandatory objectives; achievement system tracks player-discovered accomplishments",
         "params": {"achievement_count": 50, "hidden_achievements": 15,
                    "player_journal_system": True, "shareable_blueprints": True}},
        {"name": "Procedural Biomes", "category": "exploration",
         "desc": "Temperature and humidity noise maps generate distinct biome zones with unique resources",
         "params": {"biome_count": 10, "noise_scale": 0.005, "transition_zone_width": 16,
                    "underground_layers": 3}},
        {"name": "Contraption Logic", "category": "crafting",
         "desc": "Programmable logic blocks (AND, OR, NOT, timers, sensors) for automated machinery",
         "params": {"logic_gates": ["and", "or", "not", "xor", "nand", "nor"],
                    "max_circuit_depth": 12, "signal_propagation_delay": 1}},
    ],
}

_GENRE_PROGRESSION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "platformer": {"curve": "linear", "max_level": 40, "xp_per_level_base": 100,
                   "xp_growth_factor": 1.05, "unlockables_per_level": 0.3},
    "rpg": {"curve": "exponential", "max_level": 99, "xp_per_level_base": 50,
             "xp_growth_factor": 1.15, "unlockables_per_level": 1.5},
    "strategy": {"curve": "stepped", "max_level": 5, "xp_per_level_base": 500,
                 "xp_growth_factor": 2.0, "unlockables_per_level": 3.0},
    "puzzle": {"curve": "linear", "max_level": 100, "xp_per_level_base": 1,
               "xp_growth_factor": 1.0, "unlockables_per_level": 1.0},
    "shooter": {"curve": "linear", "max_level": 55, "xp_per_level_base": 200,
                "xp_growth_factor": 1.08, "unlockables_per_level": 0.8},
    "racing": {"curve": "logarithmic", "max_level": 50, "xp_per_level_base": 150,
               "xp_growth_factor": 1.03, "unlockables_per_level": 0.6},
    "simulation": {"curve": "sigmoid", "max_level": 20, "xp_per_level_base": 300,
                   "xp_growth_factor": 1.12, "unlockables_per_level": 2.0},
    "adventure": {"curve": "stepped", "max_level": 15, "xp_per_level_base": 200,
                  "xp_growth_factor": 1.1, "unlockables_per_level": 1.2},
    "fighting": {"curve": "linear", "max_level": 30, "xp_per_level_base": 80,
                 "xp_growth_factor": 1.04, "unlockables_per_level": 0.5},
    "roguelike": {"curve": "logarithmic", "max_level": 25, "xp_per_level_base": 120,
                  "xp_growth_factor": 1.06, "unlockables_per_level": 2.5},
    "metroidvania": {"curve": "stepped", "max_level": 20, "xp_per_level_base": 150,
                     "xp_growth_factor": 1.07, "unlockables_per_level": 1.8},
    "survival": {"curve": "logarithmic", "max_level": 50, "xp_per_level_base": 200,
                 "xp_growth_factor": 1.05, "unlockables_per_level": 1.0},
    "horror": {"curve": "linear", "max_level": 12, "xp_per_level_base": 100,
               "xp_growth_factor": 1.02, "unlockables_per_level": 0.3},
    "visual_novel": {"curve": "linear", "max_level": 1, "xp_per_level_base": 1,
                     "xp_growth_factor": 1.0, "unlockables_per_level": 0.0},
    "sandbox": {"curve": "logarithmic", "max_level": 30, "xp_per_level_base": 500,
                "xp_growth_factor": 1.08, "unlockables_per_level": 1.5},
}

_GENRE_ECONOMY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "platformer": {"currencies": ["coins", "gems"], "sinks": ["power_ups", "cosmetics", "extra_lives"],
                   "sources": ["collectibles", "level_completion", "challenges"],
                   "inflation_rate": 0.01},
    "rpg": {"currencies": ["gold", "reputation", "crafting_materials"],
            "sinks": ["equipment", "consumables", "training", "enchanting"],
            "sources": ["quests", "monster_drops", "trading", "crafting_sales"],
            "inflation_rate": 0.03},
    "strategy": {"currencies": ["gold", "wood", "stone", "research_points"],
                 "sinks": ["unit_production", "building", "technology"],
                 "sources": ["taxation", "resource_nodes", "trade_routes"],
                 "inflation_rate": 0.02},
    "puzzle": {"currencies": ["stars", "hints"], "sinks": ["hint_purchase", "skip_level"],
               "sources": ["level_completion", "bonus_objectives"],
               "inflation_rate": 0.0},
    "shooter": {"currencies": ["credits", "premium_tokens"],
                "sinks": ["weapon_skins", "attachments", "battle_pass"],
                "sources": ["match_rewards", "challenges", "rank_rewards"],
                "inflation_rate": 0.04},
    "racing": {"currencies": ["cash", "gold_nuts", "blueprints"],
               "sinks": ["car_upgrades", "new_vehicles", "customization"],
               "sources": ["race_winnings", "sponsorships", "daily_events"],
               "inflation_rate": 0.02},
    "simulation": {"currencies": ["simoleons", "influence", "research"],
                   "sinks": ["infrastructure", "services", "policies"],
                   "sources": ["taxation", "exports", "achievements"],
                   "inflation_rate": 0.05},
    "adventure": {"currencies": ["coins", "clues", "friendship"],
                  "sinks": ["items", "information", "travel"],
                  "sources": ["exploration", "dialogue", "quest_completion"],
                  "inflation_rate": 0.01},
    "fighting": {"currencies": ["fight_money", "costume_tokens"],
                 "sinks": ["characters", "costumes", "colors", "titles"],
                 "sources": ["match_wins", "combo_challenges", "ranked_seasons"],
                 "inflation_rate": 0.01},
    "roguelike": {"currencies": ["souls", "blood_shards"],
                  "sinks": ["meta_upgrades", "starting_items", "run_modifiers"],
                  "sources": ["run_completion", "boss_defeats", "challenge_rooms"],
                  "inflation_rate": 0.0},
    "metroidvania": {"currencies": ["energy", "artifacts"],
                     "sinks": ["ability_upgrades", "map_data", "equipment"],
                     "sources": ["enemy_drops", "secret_rooms", "boss_defeats"],
                     "inflation_rate": 0.0},
    "survival": {"currencies": ["scrap", "rations", "blueprints"],
                 "sinks": ["crafting", "building", "research"],
                 "sources": ["scavenging", "farming", "trading"],
                 "inflation_rate": 0.02},
    "horror": {"currencies": ["matches", "ammo", "herbs"],
               "sinks": ["light_sources", "defense", "healing"],
               "sources": ["environment_looting", "safe_room_caches"],
               "inflation_rate": 0.0},
    "visual_novel": {"currencies": [],
                     "sinks": ["gallery_unlocks", "music_player"],
                     "sources": ["route_completion", "achievement_flags"],
                     "inflation_rate": 0.0},
    "sandbox": {"currencies": [],
                "sinks": ["crafting", "trading_with_villagers"],
                "sources": ["mining", "farming", "mob_drops"],
                "inflation_rate": 0.0},
}

_GENRE_REWARD_TEMPLATES: Dict[str, List[str]] = {
    "platformer": ["Extra Life", "Speed Boost", "Double Jump Token", "Shield Power-Up",
                   "Coin Magnet", "Checkpoint Unlock"],
    "rpg": ["Legendary Sword", "Skill Point", "Attribute Elixir", "Rare Armor Set",
            "Companion Unlock", "Mount License"],
    "strategy": ["Advanced Unit Type", "Territory Expansion", "Resource Windfall",
                 "Technology Breakthrough", "Alliance Treaty", "Fortification Blueprint"],
    "puzzle": ["Star Rating", "Bonus Puzzle Pack", "Hint Token", "Theme Unlock",
               "Solution Gallery", "Time Trial Mode"],
    "shooter": ["Weapon Skin", "Attachment Unlock", "XP Boost", "Rank Badge",
                "Operator Unlock", "Finisher Move"],
    "racing": ["New Vehicle", "Performance Part", "Livery Design", "Track Unlock",
               "Crew Member", "Sponsorship Deal"],
    "simulation": ["City Landmark", "Policy Card", "Population Boost", "Trade Agreement",
                   "Disaster Immunity", "Advisor Upgrade"],
    "adventure": ["Key Item", "Map Fragment", "Character Backstory", "Fast Travel Point",
                  "Language Decoder", "Companion Perk"],
    "fighting": ["Alternate Costume", "Taunt Animation", "Stage Variation", "Color Palette",
                 "Victory Pose", "Special Intro"],
    "roguelike": ["Synergy Item", "Curse Removal", "Starting Gift", "Reroll Token",
                  "Revive Charm", "Map Reveal Scroll"],
    "metroidvania": ["Movement Upgrade", "Area Map", "Health Expansion", "Energy Tank",
                     "Weapon Module", "Lore Entry"],
    "survival": ["Crafting Recipe", "Base Module", "Resource Cache", "Defensive Turret",
                 "Scout Drone", "Weather Gear"],
    "horror": ["Ammo Cache", "Medkit", "Battery Pack", "Safe Room Key",
               "Map Section", "Journal Page"],
    "visual_novel": ["CG Artwork", "Music Track", "Side Story", "Character Bio",
                     "Voice Line Collection", "Ending Variant"],
    "sandbox": ["Block Variant", "Tool Upgrade", "Portal Frame", "Logic Component",
                "Blueprint Book", "Aesthetic Trim"],
}

_GENRE_SCOPE_ESTIMATES: Dict[str, str] = {
    "platformer": "12-20 hours, ~40 levels, 6-8 unique mechanics",
    "rpg": "40-80 hours, open world with 50+ quests, full skill system",
    "strategy": "20-40 hours per campaign, 4-6 factions, tech tree with 40+ nodes",
    "puzzle": "8-15 hours, 100+ puzzles across 8 worlds with escalating complexity",
    "shooter": "10-30 hours campaign, 15+ multiplayer maps, 30+ weapons",
    "racing": "15-25 hours, 20+ tracks, 40+ vehicles with full customization",
    "simulation": "50-200+ hours, persistent world with deep interconnected systems",
    "adventure": "15-30 hours, branching narrative with 5+ endings, 20+ locations",
    "fighting": "5-15 hours story, 12-20 character roster, deep training mode",
    "roguelike": "30-100+ hours, procedurally generated, high replayability",
    "metroidvania": "15-25 hours, interconnected map with 120+ rooms, 6 boss fights",
    "survival": "30-100+ hours, procedural world, building and crafting focus",
    "horror": "6-12 hours, linear with optional exploration, focused narrative",
    "visual_novel": "10-20 hours per route, 4 routes, full voice acting optional",
    "sandbox": "100+ hours, open-ended, player-driven goals, infinite replayability",
}

# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DesignDocument:
    """Complete game design specification generated from a high-level concept."""
    doc_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    genre: GameGenre = GameGenre.PLATFORMER
    description: str = ""
    target_audience: str = "core"
    platform: TargetPlatform = TargetPlatform.WEB
    mechanics: List[MechanicSpec] = field(default_factory=list)
    systems: List[MechanicSpec] = field(default_factory=list)
    progression: Optional[ProgressionSystem] = None
    economy: Optional[EconomySystem] = None
    narrative: Dict[str, Any] = field(default_factory=dict)
    estimated_scope: str = ""
    created_at: float = field(default_factory=_time_module.time)
    current_phase: DesignPhase = DesignPhase.CONCEPT
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "genre": self.genre.value,
            "description": self.description,
            "target_audience": self.target_audience,
            "platform": self.platform.value,
            "mechanics_count": len(self.mechanics),
            "systems_count": len(list(self.systems) if isinstance(self.systems, list) else []),
            "progression": self.progression.to_dict() if self.progression else None,
            "economy": self.economy.to_dict() if self.economy else None,
            "narrative": dict(self.narrative),
            "estimated_scope": self.estimated_scope,
            "created_at": self.created_at,
            "current_phase": self.current_phase.value,
            "tags": list(self.tags),
        }


@dataclass
class MechanicSpec:
    """Specification for a single game mechanic with parameters and interaction rules."""
    mechanic_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: str = "interaction"
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    rules: List[str] = field(default_factory=list)
    interactions: List[str] = field(default_factory=list)
    complexity_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mechanic_id": self.mechanic_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "parameters": dict(self.parameters),
            "rules": list(self.rules),
            "interactions": list(self.interactions),
            "complexity_score": self.complexity_score,
        }


@dataclass
class ProgressionSystem:
    """Player progression design including leveling curve, rewards, and unlock patterns."""
    prog_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    level_type: str = "player_level"
    levels: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[str] = field(default_factory=list)
    unlockables: List[str] = field(default_factory=list)
    curve_type: ProgressionCurveType = ProgressionCurveType.LINEAR
    max_level: int = 20

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prog_id": self.prog_id,
            "name": self.name,
            "level_type": self.level_type,
            "levels": list(self.levels),
            "rewards": list(self.rewards),
            "unlockables": list(self.unlockables),
            "curve_type": self.curve_type.value,
            "max_level": self.max_level,
        }


@dataclass
class EconomySystem:
    """Game economy design with currencies, resources, sinks, sources, and balance targets."""
    economy_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    currencies: List[str] = field(default_factory=list)
    resources: Dict[str, float] = field(default_factory=dict)
    sinks: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    inflation_rate: float = 0.0
    balance_targets: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "economy_id": self.economy_id,
            "currencies": list(self.currencies),
            "resources": dict(self.resources),
            "sinks": list(self.sinks),
            "sources": list(self.sources),
            "inflation_rate": self.inflation_rate,
            "balance_targets": dict(self.balance_targets),
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _compute_xp_for_level(level: int, base: float, growth: float, curve: ProgressionCurveType) -> float:
    """Compute XP required for a given level based on the progression curve type."""
    if curve == ProgressionCurveType.LINEAR:
        return base + (base * growth * (level - 1))
    elif curve == ProgressionCurveType.EXPONENTIAL:
        return base * (growth ** (level - 1))
    elif curve == ProgressionCurveType.LOGARITHMIC:
        import math
        return base * (1 + growth * math.log(max(level, 1)))
    elif curve == ProgressionCurveType.STEPPED:
        step_size = max(1, 20 // 5)
        step = (level - 1) // step_size
        return base * (1 + growth * level) * (1 + step * 0.5)
    elif curve == ProgressionCurveType.SIGMOID:
        import math
        midpoint = 20 / 2
        steepness = 0.2
        return base + (base * 9) / (1 + math.exp(-steepness * (level - midpoint)))
    return base * level


def _roll_complexity() -> float:
    """Generate a complexity score with a normal-ish distribution around 3.0."""
    return round(max(0.5, min(10.0, random.gauss(3.0, 1.5))), 1)


def _generate_rules(mechanic_name: str, params: Dict[str, Any]) -> List[str]:
    """Generate natural-language rules based on mechanic parameters."""
    rules: List[str] = []
    for key, value in params.items():
        if isinstance(value, (int, float)):
            rules.append(f"{mechanic_name} uses {key} with a base value of {value}")
        elif isinstance(value, list) and all(isinstance(v, str) for v in value):
            rules.append(f"{mechanic_name} supports {key}: {', '.join(str(v) for v in value)}")
        elif isinstance(value, bool):
            state = "enabled" if value else "disabled"
            rules.append(f"{mechanic_name} has {key} {state}")
    if not rules:
        rules.append(f"{mechanic_name} operates with default tuning parameters")
    return rules


def _generate_interactions(mechanic_name: str, category: str, genre: str) -> List[str]:
    """Generate plausible interaction descriptions with other systems."""
    interactions: List[str] = []
    if category == "movement":
        interactions.append(f"{mechanic_name} modifies traversal speed and affects level design pacing")
        interactions.append(f"{mechanic_name} interacts with obstacle placement in {genre} environments")
    elif category == "combat":
        interactions.append(f"{mechanic_name} chains into other combat actions with frame-dependent windows")
        interactions.append(f"{mechanic_name} scales with player damage and defense statistics")
    elif category == "resource":
        interactions.append(f"{mechanic_name} integrates with the game economy through earn and spend cycles")
        interactions.append(f"{mechanic_name} gates access to certain abilities or content thresholds")
    elif category == "progression":
        interactions.append(f"{mechanic_name} unlocks sequentially based on player level milestones")
        interactions.append(f"{mechanic_name} creates meaningful choices between alternative upgrade paths")
    elif category == "social":
        interactions.append(f"{mechanic_name} affects NPC disposition and unlocks new dialogue options")
        interactions.append(f"{mechanic_name} propagates consequences through the relationship network")
    elif category == "exploration":
        interactions.append(f"{mechanic_name} reveals hidden content and rewards thorough investigation")
        interactions.append(f"{mechanic_name} connects to the map system and backtracking incentives")
    elif category == "crafting":
        interactions.append(f"{mechanic_name} consumes gathered resources to produce usable items")
        interactions.append(f"{mechanic_name} tiers up with higher-grade materials producing stronger results")
    else:
        interactions.append(f"{mechanic_name} integrates with core {genre} gameplay loop")
        interactions.append(f"{mechanic_name} provides feedback through UI and audio channels")
    return interactions


# =============================================================================
# Singleton Agent
# =============================================================================

class GameDesignerAgent:
    """
    Autonomous AI game designer that generates complete game designs from
    high-level descriptions. Produces comprehensive design documents, mechanics
    specifications, progression systems, and game economy models tailored to
    different genres for the AI-native game engine.

    Usage:
        designer = get_game_designer()
        doc = designer.generate_full_design("Star Vault", GameGenre.METROIDVANIA,
            "A cosmic horror metroidvania set aboard a derelict space station")
        mechanics = designer.define_mechanics(doc.doc_id, count=6)
        prog = designer.design_progression(doc.doc_id, levels_count=30)
        economy = designer.design_economy(doc.doc_id)
        evaluation = designer.evaluate_design(doc.doc_id)
    """

    _instance: Optional["GameDesignerAgent"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GameDesignerAgent":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameDesignerAgent":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._designs: Dict[str, DesignDocument] = {}
        self._mechanics_store: Dict[str, List[MechanicSpec]] = {}
        self._progression_store: Dict[str, ProgressionSystem] = {}
        self._economy_store: Dict[str, EconomySystem] = {}
        self._evaluation_cache: Dict[str, Dict[str, Any]] = {}
        self._total_designs_created: int = 0
        self._total_mechanics_defined: int = 0
        self._recent_actions: deque = deque(maxlen=50)

    # ------------------------------------------------------------------
    # Core Design Operations
    # ------------------------------------------------------------------

    def create_design(
        self,
        title: str,
        genre: GameGenre,
        description: str,
        target_audience: str = "core",
        platform: TargetPlatform = TargetPlatform.WEB,
    ) -> DesignDocument:
        """Create a new design document with genre-specific defaults and estimated scope."""
        genre_key = genre.value
        doc = DesignDocument(
            title=title,
            genre=genre,
            description=description,
            target_audience=target_audience,
            platform=platform,
            estimated_scope=_GENRE_SCOPE_ESTIMATES.get(genre_key, "scope to be determined"),
            tags=[genre_key, target_audience],
        )
        self._designs[doc.doc_id] = doc
        self._total_designs_created += 1
        self._recent_actions.append({
            "action": "create_design",
            "doc_id": doc.doc_id,
            "title": title,
            "genre": genre_key,
            "timestamp": _time_module.time(),
        })
        return doc

    def define_mechanics(self, doc_id: str, count: int = 6) -> List[MechanicSpec]:
        """Generate a set of genre-appropriate mechanics for the given design document."""
        doc = self._designs.get(doc_id)
        if doc is None:
            return []

        genre_key = doc.genre.value
        templates = _GENRE_MECHANIC_TEMPLATES.get(genre_key, [])
        if not templates:
            return []

        mechanics: List[MechanicSpec] = []
        shuffled = random.sample(templates, min(count, len(templates)))

        for tmpl in shuffled:
            params = dict(tmpl.get("params", {}))
            param_keys = list(params.keys())
            if param_keys:
                jitter_key = random.choice(param_keys)
                original = params[jitter_key]
                if isinstance(original, (int, float)):
                    params[jitter_key] = round(original * random.uniform(0.85, 1.15), 2)
                elif isinstance(original, list) and len(original) > 0:
                    params["variant"] = random.choice(original)

            rules = _generate_rules(tmpl["name"], params)
            interactions = _generate_interactions(tmpl["name"], tmpl["category"], genre_key)
            complexity = _roll_complexity()

            spec = MechanicSpec(
                name=tmpl["name"],
                category=tmpl["category"],
                description=tmpl["desc"],
                parameters=params,
                rules=rules,
                interactions=interactions,
                complexity_score=complexity,
            )
            mechanics.append(spec)

        self._mechanics_store[doc_id] = mechanics
        doc.mechanics = mechanics
        doc.current_phase = DesignPhase.MECHANICS
        self._total_mechanics_defined += len(mechanics)
        self._recent_actions.append({
            "action": "define_mechanics",
            "doc_id": doc_id,
            "count": len(mechanics),
            "timestamp": _time_module.time(),
        })
        return mechanics

    def design_progression(self, doc_id: str, levels_count: int = 20) -> Optional[ProgressionSystem]:
        """Design a progression system with leveled XP curve and genre-appropriate rewards."""
        doc = self._designs.get(doc_id)
        if doc is None:
            return None

        genre_key = doc.genre.value
        defaults = _GENRE_PROGRESSION_DEFAULTS.get(genre_key, {})
        curve_str = defaults.get("curve", "linear")
        curve_type = ProgressionCurveType(curve_str)
        max_level = min(levels_count, defaults.get("max_level", 50))
        base_xp = defaults.get("xp_per_level_base", 100)
        growth = defaults.get("xp_growth_factor", 1.05)
        unlock_per_level = defaults.get("unlockables_per_level", 1.0)

        levels: List[Dict[str, Any]] = []
        cumulative_xp = 0.0
        for lvl in range(1, max_level + 1):
            xp_needed = _compute_xp_for_level(lvl, base_xp, growth, curve_type)
            cumulative_xp += xp_needed
            levels.append({
                "level": lvl,
                "xp_required": round(xp_needed, 1),
                "cumulative_xp": round(cumulative_xp, 1),
            })

        reward_pool = _GENRE_REWARD_TEMPLATES.get(genre_key, ["Basic Reward"])
        total_rewards = max(1, int(max_level * unlock_per_level))
        rewards = [random.choice(reward_pool) for _ in range(total_rewards)]

        unlock_indices: List[int] = []
        step = max(1, max_level // max(1, total_rewards))
        for i in range(total_rewards):
            unlock_indices.append(min(max_level, (i + 1) * step))
        unlockables = [
            f"Level {lvl}: {rewards[i]}" if i < len(rewards) else f"Level {lvl}: Bonus Unlock"
            for i, lvl in enumerate(unlock_indices)
        ]

        prog = ProgressionSystem(
            name=f"{doc.title} Progression",
            level_type="player_level",
            levels=levels,
            rewards=rewards,
            unlockables=unlockables,
            curve_type=curve_type,
            max_level=max_level,
        )

        self._progression_store[doc_id] = prog
        doc.progression = prog
        doc.current_phase = DesignPhase.PROGRESSION
        self._recent_actions.append({
            "action": "design_progression",
            "doc_id": doc_id,
            "max_level": max_level,
            "curve": curve_str,
            "timestamp": _time_module.time(),
        })
        return prog

    def design_economy(self, doc_id: str) -> Optional[EconomySystem]:
        """Design an economy system with genre-appropriate currencies, sinks, and sources."""
        doc = self._designs.get(doc_id)
        if doc is None:
            return None

        genre_key = doc.genre.value
        defaults = _GENRE_ECONOMY_DEFAULTS.get(genre_key, {})
        currencies = list(defaults.get("currencies", []))
        sinks = list(defaults.get("sinks", []))
        sources = list(defaults.get("sources", []))
        inflation_rate = defaults.get("inflation_rate", 0.0)

        resources: Dict[str, float] = {}
        if currencies:
            initial_value = 1000.0
            for currency in currencies:
                resources[currency] = round(initial_value * random.uniform(0.5, 2.0), 2)

        balance_targets = {
            "income_per_hour": round(random.uniform(50, 500), 2),
            "spend_per_hour": round(random.uniform(40, 480), 2),
            "net_gain_target": round(random.uniform(5, 50), 2),
            "inflation_ceiling": round(inflation_rate * 3, 4),
            "player_wealth_gini_target": round(random.uniform(0.25, 0.55), 2),
            "sink_saturation_threshold": 0.8,
        }

        economy = EconomySystem(
            currencies=currencies,
            resources=resources,
            sinks=sinks,
            sources=sources,
            inflation_rate=inflation_rate,
            balance_targets=balance_targets,
        )

        self._economy_store[doc_id] = economy
        doc.economy = economy
        doc.current_phase = DesignPhase.ECONOMY
        self._recent_actions.append({
            "action": "design_economy",
            "doc_id": doc_id,
            "currency_count": len(currencies),
            "timestamp": _time_module.time(),
        })
        return economy

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_design(self, doc_id: str) -> Dict[str, Any]:
        """Evaluate a design document across feasibility, fun factor, balance, and completeness."""
        doc = self._designs.get(doc_id)
        if doc is None:
            return {"error": "design not found"}

        genre_key = doc.genre.value

        mechanic_count = len(doc.mechanics) if doc.mechanics else 0
        has_progression = doc.progression is not None
        has_economy = doc.economy is not None

        feasibility = 0.0
        if has_progression and has_economy:
            feasibility = 0.9
        elif has_progression or has_economy:
            feasibility = 0.7
        elif mechanic_count > 0:
            feasibility = 0.5
        else:
            feasibility = 0.3

        genre_fun_index = {
            "platformer": 0.75, "rpg": 0.8, "strategy": 0.7, "puzzle": 0.65,
            "shooter": 0.78, "racing": 0.68, "simulation": 0.62, "adventure": 0.75,
            "fighting": 0.72, "roguelike": 0.85, "metroidvania": 0.8, "survival": 0.73,
            "horror": 0.7, "visual_novel": 0.6, "sandbox": 0.82,
        }
        base_fun = genre_fun_index.get(genre_key, 0.7)
        mechanic_bonus = min(0.2, mechanic_count * 0.03)
        progression_bonus = 0.05 if has_progression else 0.0
        economy_bonus = 0.05 if has_economy else 0.0
        fun_factor = round(min(1.0, base_fun + mechanic_bonus + progression_bonus + economy_bonus), 2)

        balance = 0.0
        if has_economy and has_progression:
            inflation = doc.economy.inflation_rate if doc.economy else 0.0
            if inflation < 0.02:
                balance = 0.9
            elif inflation < 0.05:
                balance = 0.75
            else:
                balance = 0.6
        elif has_progression:
            balance = 0.65
        elif has_economy:
            balance = 0.55
        else:
            balance = 0.4
        balance_noise = random.uniform(-0.05, 0.05)
        balance = round(min(1.0, max(0.0, balance + balance_noise)), 2)

        completeness = 0.0
        phase_weights = {
            DesignPhase.CONCEPT: 0.1,
            DesignPhase.MECHANICS: 0.3,
            DesignPhase.SYSTEMS: 0.2,
            DesignPhase.PROGRESSION: 0.25,
            DesignPhase.ECONOMY: 0.15,
            DesignPhase.NARRATIVE: 0.1,
            DesignPhase.LEVELS: 0.1,
            DesignPhase.POLISH: 0.1,
        }
        current_weight = phase_weights.get(doc.current_phase, 0.1)
        detail_bonus = 0.0
        if mechanic_count > 0:
            detail_bonus += 0.15
        if has_progression:
            detail_bonus += 0.15
        if has_economy:
            detail_bonus += 0.1
        if doc.narrative:
            detail_bonus += 0.1
        completeness = round(min(1.0, current_weight + detail_bonus), 2)

        evaluation = {
            "doc_id": doc_id,
            "title": doc.title,
            "genre": genre_key,
            "feasibility": feasibility,
            "fun_factor": fun_factor,
            "balance": balance,
            "completeness": completeness,
            "overall_score": round((feasibility + fun_factor + balance + completeness) / 4, 2),
            "recommendations": [],
            "evaluated_at": _time_module.time(),
        }

        if feasibility < 0.6:
            evaluation["recommendations"].append(
                "Consider defining both progression and economy systems to improve feasibility")
        if fun_factor < 0.7:
            evaluation["recommendations"].append(
                "Add more distinct mechanics to increase gameplay variety and engagement")
        if balance < 0.6:
            evaluation["recommendations"].append(
                "Review economy inflation rate and progression curve for better balance")
        if completeness < 0.5:
            evaluation["recommendations"].append(
                "Continue through remaining design phases to achieve a fully specified design")

        self._evaluation_cache[doc_id] = evaluation
        self._recent_actions.append({
            "action": "evaluate_design",
            "doc_id": doc_id,
            "overall_score": evaluation["overall_score"],
            "timestamp": _time_module.time(),
        })
        return evaluation

    # ------------------------------------------------------------------
    # Full Design Pipeline
    # ------------------------------------------------------------------

    def generate_full_design(
        self,
        title: str,
        genre: GameGenre,
        description: str,
        target_audience: str = "core",
        platform: TargetPlatform = TargetPlatform.WEB,
    ) -> DesignDocument:
        """Run the complete end-to-end design pipeline: create, define mechanics,
        design progression, design economy, and build narrative scaffolding."""
        doc = self.create_design(title, genre, description, target_audience, platform)

        genre_key = genre.value
        defaults_prog = _GENRE_PROGRESSION_DEFAULTS.get(genre_key, {})
        default_levels = defaults_prog.get("max_level", 20)
        levels_count = min(default_levels, 30)

        self.define_mechanics(doc.doc_id, count=6)
        self.design_progression(doc.doc_id, levels_count=levels_count)
        self.design_economy(doc.doc_id)

        narrative = {
            "tone": self._derive_tone(genre_key, description),
            "setting_summary": description,
            "suggested_chapters": self._estimate_chapters(genre_key),
            "core_conflict": self._derive_conflict(genre_key),
            "themes": self._derive_themes(genre_key),
            "player_role": self._derive_player_role(genre_key),
        }
        doc.narrative = narrative
        doc.current_phase = DesignPhase.POLISH
        doc.tags.extend([genre_key, "auto-generated", target_audience])

        self._recent_actions.append({
            "action": "generate_full_design",
            "doc_id": doc.doc_id,
            "title": title,
            "genre": genre_key,
            "timestamp": _time_module.time(),
        })
        return doc

    # ------------------------------------------------------------------
    # Narrative Derivation Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_tone(genre_key: str, description: str) -> str:
        tone_map = {
            "platformer": "lighthearted and energetic",
            "rpg": "epic and mythic with moments of intimacy",
            "strategy": "calculated and cerebral",
            "puzzle": "curious and contemplative",
            "shooter": "tense and adrenaline-driven",
            "racing": "fast-paced and competitive",
            "simulation": "systematic and meditative",
            "adventure": "wondrous and discovery-focused",
            "fighting": "intense and dramatic",
            "roguelike": "bleak yet hopeful, with dark humor",
            "metroidvania": "atmospheric and isolating",
            "survival": "desperate and resourceful",
            "horror": "dread-inducing and oppressive",
            "visual_novel": "intimate and character-driven",
            "sandbox": "free-form and player-authored",
        }
        return tone_map.get(genre_key, "balanced and engaging")

    @staticmethod
    def _estimate_chapters(genre_key: str) -> int:
        chapter_map = {
            "platformer": 8, "rpg": 12, "strategy": 6, "puzzle": 8,
            "shooter": 10, "racing": 5, "simulation": 4, "adventure": 7,
            "fighting": 6, "roguelike": 5, "metroidvania": 6, "survival": 5,
            "horror": 6, "visual_novel": 4, "sandbox": 1,
        }
        return chapter_map.get(genre_key, 6)

    @staticmethod
    def _derive_conflict(genre_key: str) -> str:
        conflict_map = {
            "platformer": "hero versus environmental obstacles and a charismatic villain",
            "rpg": "party versus a world-threatening cosmic or political force",
            "strategy": "faction versus faction for territorial and ideological dominance",
            "puzzle": "player versus increasingly complex logical constraints",
            "shooter": "squad versus opposing force in high-stakes military engagements",
            "racing": "racer versus the track, the clock, and rival competitors",
            "simulation": "player versus entropy and resource constraints",
            "adventure": "protagonist versus mystery, environment, and personal limitation",
            "fighting": "fighter versus fighter in a tournament of escalating stakes",
            "roguelike": "lone adventurer versus an ever-shifting hostile labyrinth",
            "metroidvania": "explorer versus sealed world and its guardians",
            "survival": "survivor versus nature, scarcity, and persistent threats",
            "horror": "protagonist versus an unknowable and relentless entity",
            "visual_novel": "characters versus emotional barriers, secrets, and fate",
            "sandbox": "player versus their own ambition and creativity",
        }
        return conflict_map.get(genre_key, "protagonist versus external and internal challenges")

    @staticmethod
    def _derive_themes(genre_key: str) -> List[str]:
        theme_map = {
            "platformer": ["perseverance", "precision", "joy of movement"],
            "rpg": ["growth", "sacrifice", "identity", "companionship"],
            "strategy": ["leadership", "consequence", "resourcefulness"],
            "puzzle": ["insight", "pattern recognition", "patience"],
            "shooter": ["camaraderie", "survival", "moral ambiguity"],
            "racing": ["mastery", "rivalry", "speed as freedom"],
            "simulation": ["emergence", "stewardship", "cause and effect"],
            "adventure": ["curiosity", "discovery", "connection"],
            "fighting": ["discipline", "honor", "self-improvement"],
            "roguelike": ["adaptation", "acceptance of loss", "incremental growth"],
            "metroidvania": ["isolation", "archaeology of place", "unlocking potential"],
            "survival": ["resilience", "ingenuity", "the value of scarcity"],
            "horror": ["fear as teacher", "the unknown", "vulnerability"],
            "visual_novel": ["empathy", "choice and consequence", "intersecting lives"],
            "sandbox": ["creativity", "autonomy", "self-expression"],
        }
        return theme_map.get(genre_key, ["challenge", "progression", "achievement"])

    @staticmethod
    def _derive_player_role(genre_key: str) -> str:
        role_map = {
            "platformer": "agile hero navigating treacherous environments",
            "rpg": "customizable adventurer shaping the world through choices",
            "strategy": "commander overseeing armies and empires from above",
            "puzzle": "problem-solver unraveling intricate logical challenges",
            "shooter": "soldier or operative in tactical combat scenarios",
            "racing": "driver competing for supremacy on diverse tracks",
            "simulation": "overseer managing complex interconnected systems",
            "adventure": "explorer uncovering secrets in a rich narrative world",
            "fighting": "combatant mastering a character's unique fighting style",
            "roguelike": "determined challenger facing procedurally generated trials",
            "metroidvania": "lone wanderer unlocking the secrets of an interconnected world",
            "survival": "resourceful survivor building and defending against the odds",
            "horror": "vulnerable protagonist navigating a terrifying ordeal",
            "visual_novel": "reader-protagonist making choices that shape personal relationships",
            "sandbox": "creator defining their own goals in an open world",
        }
        return role_map.get(genre_key, "player engaging with the core gameplay loop")

    # ------------------------------------------------------------------
    # Query and Stats
    # ------------------------------------------------------------------

    def list_designs(self) -> List[DesignDocument]:
        """Return all design documents sorted by creation time (most recent first)."""
        return sorted(
            self._designs.values(),
            key=lambda d: d.created_at,
            reverse=True,
        )

    def get_design(self, doc_id: str) -> Optional[DesignDocument]:
        """Retrieve a specific design document by ID."""
        return self._designs.get(doc_id)

    def get_mechanics_for_design(self, doc_id: str) -> List[MechanicSpec]:
        """Retrieve all mechanics defined for a given design."""
        return self._mechanics_store.get(doc_id, [])

    def get_progression_for_design(self, doc_id: str) -> Optional[ProgressionSystem]:
        """Retrieve the progression system for a given design."""
        return self._progression_store.get(doc_id)

    def get_economy_for_design(self, doc_id: str) -> Optional[EconomySystem]:
        """Retrieve the economy system for a given design."""
        return self._economy_store.get(doc_id)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about all designs managed by this agent."""
        genre_counts: Dict[str, int] = {}
        total_mechanics = 0
        for doc in self._designs.values():
            genre_counts[doc.genre.value] = genre_counts.get(doc.genre.value, 0) + 1
            if doc.mechanics:
                total_mechanics += len(doc.mechanics)

        return {
            "total_designs_created": self._total_designs_created,
            "active_designs": len(self._designs),
            "total_mechanics_defined": self._total_mechanics_defined,
            "designs_by_genre": genre_counts,
            "total_mechanics_in_designs": total_mechanics,
            "designs_with_progression": len(self._progression_store),
            "designs_with_economy": len(self._economy_store),
            "evaluations_cached": len(self._evaluation_cache),
            "recent_actions": list(self._recent_actions),
        }

    def export_design_json(self, doc_id: str) -> Optional[str]:
        """Export a design document as a JSON string."""
        doc = self._designs.get(doc_id)
        if doc is None:
            return None
        return json.dumps(doc.to_dict(), indent=2, default=str)

    def delete_design(self, doc_id: str) -> bool:
        """Remove a design and all associated data."""
        if doc_id not in self._designs:
            return False
        del self._designs[doc_id]
        self._mechanics_store.pop(doc_id, None)
        self._progression_store.pop(doc_id, None)
        self._economy_store.pop(doc_id, None)
        self._evaluation_cache.pop(doc_id, None)
        self._recent_actions.append({
            "action": "delete_design",
            "doc_id": doc_id,
            "timestamp": _time_module.time(),
        })
        return True


# =============================================================================
# Module-Level Accessor
# =============================================================================

def get_game_designer() -> GameDesignerAgent:
    """Return the singleton GameDesignerAgent instance."""
    return GameDesignerAgent.get_instance()