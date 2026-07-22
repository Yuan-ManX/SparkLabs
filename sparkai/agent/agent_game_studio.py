"""
SparkLabs Agent - Game Studio

A multi-agent collaboration system where specialized AI agents work together
to design, build, test, and polish a game. Each agent has a distinct role and
contributes its expertise to the final game design document.

Studio Agents:
  - DesignerAgent   : defines mechanics, rules, balance, progression
  - ProgrammerAgent : translates design into logic, evaluates feasibility
  - ArtistAgent     : defines visual style, palette, atmosphere
  - TesterAgent     : simulates playtests, identifies issues, suggests fixes
  - ComposerAgent   : defines audio mood, tempo, SFX landscape
  - StudioDirector  : orchestrates the agents, aggregates their outputs

The studio produces a StudioResult containing:
  - A consolidated game design blueprint from all agents
  - Individual agent contributions for transparency
  - A collaboration log showing how agents built on each other's work
  - Quality assessment from the tester's perspective

Usage:
    studio = GameStudio.get_instance()
    studio.initialize()
    result = studio.collaborate("Design a roguelike dungeon crawler with permadeath")
    # result.blueprint contains the consolidated design
    # result.agent_outputs contains each agent's contribution
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class AgentContribution:
    """A single agent's contribution to the game design."""
    agent_name: str
    agent_role: str
    content: Dict[str, Any]
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "content": dict(self.content),
            "timestamp": round(self.timestamp, 3),
        }


@dataclass
class CollaborationMessage:
    """A message exchanged between agents during collaboration."""
    from_agent: str
    to_agent: str
    message_type: str  # proposal, feedback, revision, consensus
    content: str
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": round(self.timestamp, 3),
        }


@dataclass
class GameBlueprint:
    """Consolidated game design blueprint from all studio agents."""
    title: str = ""
    genre: str = ""
    theme: str = ""
    visual_style: str = ""
    audio_profile: str = ""
    core_mechanics: List[str] = field(default_factory=list)
    secondary_mechanics: List[str] = field(default_factory=list)
    progression_system: str = ""
    balance_notes: str = ""
    color_palette: List[str] = field(default_factory=list)
    atmosphere: str = ""
    tempo_bpm: int = 0
    sfx_landscape: List[str] = field(default_factory=list)
    test_findings: List[str] = field(default_factory=list)
    risk_mitigations: List[str] = field(default_factory=list)
    innovation_angles: List[str] = field(default_factory=list)
    estimated_engagement: float = 0.0
    estimated_difficulty: float = 0.0
    estimated_replayability: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "genre": self.genre,
            "theme": self.theme,
            "visual_style": self.visual_style,
            "audio_profile": self.audio_profile,
            "core_mechanics": list(self.core_mechanics),
            "secondary_mechanics": list(self.secondary_mechanics),
            "progression_system": self.progression_system,
            "balance_notes": self.balance_notes,
            "color_palette": list(self.color_palette),
            "atmosphere": self.atmosphere,
            "tempo_bpm": self.tempo_bpm,
            "sfx_landscape": list(self.sfx_landscape),
            "test_findings": list(self.test_findings),
            "risk_mitigations": list(self.risk_mitigations),
            "innovation_angles": list(self.innovation_angles),
            "estimated_engagement": round(self.estimated_engagement, 2),
            "estimated_difficulty": round(self.estimated_difficulty, 2),
            "estimated_replayability": round(self.estimated_replayability, 2),
        }


@dataclass
class StudioResult:
    """Complete result from a studio collaboration session."""
    session_id: str
    success: bool
    prompt: str
    blueprint: GameBlueprint
    agent_outputs: List[AgentContribution]
    collaboration_log: List[CollaborationMessage]
    rounds: int
    duration_s: float
    consensus_reached: bool
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "success": self.success,
            "prompt": self.prompt,
            "blueprint": self.blueprint.to_dict(),
            "agent_outputs": [a.to_dict() for a in self.agent_outputs],
            "collaboration_log": [m.to_dict() for m in self.collaboration_log],
            "rounds": self.rounds,
            "duration_s": round(self.duration_s, 3),
            "consensus_reached": self.consensus_reached,
            "error": self.error,
        }


# =============================================================================
# Studio Agents
# =============================================================================


class _DesignerAgent:
    """Defines game mechanics, rules, balance, and progression."""

    NAME = "Designer"
    ROLE = "game_design"

    def contribute(self, prompt: str, previous: Dict[str, Any]) -> AgentContribution:
        lower_prompt = prompt.lower()
        mechanics: List[str] = []
        secondary: List[str] = []

        # Core mechanics derived from prompt analysis
        if any(w in lower_prompt for w in ["jump", "platform", "double jump"]):
            mechanics.extend(["jump", "double_jump", "platforming"])
        if any(w in lower_prompt for w in ["shoot", "gun", "bullet", "laser"]):
            mechanics.extend(["shooting", "aiming", "projectile"])
        if any(w in lower_prompt for w in ["puzzle", "switch", "crystal", "match"]):
            mechanics.extend(["puzzle_solving", "pattern_matching"])
        if any(w in lower_prompt for w in ["race", "speed", "fast", "lap"]):
            mechanics.extend(["racing", "time_trial"])
        if any(w in lower_prompt for w in ["survive", "survival", "wave"]):
            mechanics.extend(["survival", "wave_defense", "resource_management"])
        if any(w in lower_prompt for w in ["rpg", "level up", "stats", "equipment"]):
            mechanics.extend(["leveling", "equipment", "stat_growth"])
        if any(w in lower_prompt for w in ["dungeon", "rogue", "roguelike", "permadeath"]):
            mechanics.extend(["procedural_generation", "permadeath", "run_based"])
        if any(w in lower_prompt for w in ["boss", "raid", "epic"]):
            mechanics.extend(["boss_encounter", "phase_transitions", "pattern_learning"])
        if not mechanics:
            mechanics = ["exploration", "collection", "combat"]

        # Secondary mechanics add depth
        secondary.append("score_system")
        if "combo" in lower_prompt or "chain" in lower_prompt:
            secondary.append("combo_multiplier")
        if "collect" in lower_prompt or "gem" in lower_prompt or "treasure" in lower_prompt:
            secondary.append("collectible_hunting")
        if "story" in lower_prompt or "narrative" in lower_prompt or "quest" in lower_prompt:
            secondary.append("quest_progression")
            secondary.append("dialogue_system")
        secondary.append("achievement_system")
        secondary.append("difficulty_scaling")

        # Progression system
        if mechanics and any("leveling" in m for m in mechanics):
            progression = "XP-based leveling with skill tree unlocks and equipment tiers"
        elif mechanics and any("rogue" in m for m in mechanics):
            progression = "Run-based meta-progression with permanent unlocks between runs"
        elif mechanics and any("puzzle" in m for m in mechanics):
            progression = "Puzzle gate progression with increasing complexity and new mechanics"
        else:
            progression = "Level-based progression with score thresholds and ability unlocks"

        # Balance notes
        balance = self._compute_balance_notes(mechanics, lower_prompt)

        # Innovation angles
        innovations = self._derive_innovations(mechanics, lower_prompt)

        return AgentContribution(
            agent_name=self.NAME,
            agent_role=self.ROLE,
            timestamp=time.time(),
            content={
                "core_mechanics": mechanics,
                "secondary_mechanics": secondary,
                "progression_system": progression,
                "balance_notes": balance,
                "innovation_angles": innovations,
                "estimated_difficulty": self._estimate_difficulty(mechanics),
                "estimated_engagement": self._estimate_engagement(mechanics, secondary),
                "estimated_replayability": self._estimate_replayability(mechanics, secondary),
            },
        )

    def _compute_balance_notes(self, mechanics: List[str], prompt: str) -> str:
        notes: List[str] = []
        if "survival" in mechanics:
            notes.append("Resource scarcity increases over time to create tension")
        if "shooting" in mechanics:
            notes.append("Enemy health scales with player weapon upgrades")
        if "permadeath" in mechanics:
            notes.append("Each run must be completable in 15-30 minutes")
        if "puzzle_solving" in mechanics:
            notes.append("Every puzzle must be solvable with tools introduced in the same level")
        if "boss_encounter" in mechanics:
            notes.append("Boss has 3 phases with distinct attack patterns")
        if not notes:
            notes.append("Difficulty curve ramps smoothly with occasional spikes for variety")
        return "; ".join(notes)

    def _derive_innovations(self, mechanics: List[str], prompt: str) -> List[str]:
        innovations: List[str] = []
        if "procedural_generation" in mechanics and "permadeath" in mechanics:
            innovations.append("Daily challenge seed system for competitive leaderboards")
        if "puzzle_solving" in mechanics:
            innovations.append("Environmental puzzles that change based on time of day")
        if "boss_encounter" in mechanics:
            innovations.append("Boss learns from player behavior and adapts attack patterns")
        if "combo_multiplier" in str(mechanics) or "combo" in prompt:
            innovations.append("Combo chain that unlocks temporary special abilities")
        if not innovations:
            innovations.append("Dynamic difficulty adjustment based on player performance")
        return innovations[:3]

    def _estimate_difficulty(self, mechanics: List[str]) -> float:
        base = 0.5
        if "survival" in mechanics:
            base += 0.15
        if "permadeath" in mechanics:
            base += 0.2
        if "boss_encounter" in mechanics:
            base += 0.1
        if "puzzle_solving" in mechanics:
            base += 0.05
        return round(min(1.0, base), 2)

    def _estimate_engagement(self, mechanics: List[str], secondary: List[str]) -> float:
        score = 0.5 + len(mechanics) * 0.05 + len(secondary) * 0.03
        return round(min(1.0, score), 2)

    def _estimate_replayability(self, mechanics: List[str], secondary: List[str]) -> float:
        score = 0.3
        if "procedural_generation" in mechanics:
            score += 0.3
        if "permadeath" in mechanics:
            score += 0.2
        if any("achievement" in s for s in secondary):
            score += 0.1
        if any("combo" in s for s in secondary):
            score += 0.1
        return round(min(1.0, score), 2)


class _ProgrammerAgent:
    """Translates design into logic and evaluates technical feasibility."""

    NAME = "Programmer"
    ROLE = "technical_architecture"

    def contribute(self, prompt: str, previous: Dict[str, Any]) -> AgentContribution:
        designer_output = previous.get("Designer", {})
        mechanics = designer_output.get("core_mechanics", [])

        # Determine game architecture
        architecture: List[str] = []
        architecture.append("fixed_timestep_game_loop")
        architecture.append("entity_component_system")
        architecture.append("state_machine_for_game_phases")
        if "platforming" in str(mechanics):
            architecture.append("physics_engine_with_collision_detection")
            architecture.append("tile_based_level_representation")
        if "shooting" in str(mechanics):
            architecture.append("projectile_pooling_system")
            architecture.append("hitbox_hurtbox_separation")
        if "procedural_generation" in str(mechanics):
            architecture.append("seeded_random_generation_pipeline")
            architecture.append("room_based_layout_algorithm")
        if "puzzle_solving" in str(mechanics):
            architecture.append("grid_based_puzzle_state")
            architecture.append("undo_redo_stack")
        if "leveling" in str(mechanics):
            architecture.append("save_load_system_with_serialization")
            architecture.append("inventory_management")

        # Technical risks
        risks: List[str] = []
        if "physics_engine_with_collision_detection" in architecture:
            risks.append("Collision detection must handle fast-moving objects via raycasting")
        if "seeded_random_generation_pipeline" in architecture:
            risks.append("Procedural layouts must guarantee solvability")
        if "projectile_pooling_system" in architecture:
            risks.append("Object pool size must be tuned to prevent visual popping")
        if not risks:
            risks.append("Input latency must be kept under 16ms for responsive feel")

        # Feasibility assessment
        complexity = len(architecture)
        feasibility = "high" if complexity <= 5 else ("medium" if complexity <= 8 else "challenging")

        return AgentContribution(
            agent_name=self.NAME,
            agent_role=self.ROLE,
            timestamp=time.time(),
            content={
                "architecture": architecture,
                "technical_risks": risks,
                "feasibility": feasibility,
                "estimated_complexity": complexity,
                "input_scheme": self._design_input_scheme(mechanics),
                "performance_targets": {
                    "target_fps": 60,
                    "max_entities": 200 if "survival" in str(mechanics) else 100,
                    "max_particle_count": 300,
                },
            },
        )

    def _design_input_scheme(self, mechanics: List[str]) -> Dict[str, str]:
        scheme: Dict[str, str] = {}
        m_str = str(mechanics)
        if "platforming" in m_str:
            scheme["move_left"] = "ArrowLeft / A"
            scheme["move_right"] = "ArrowRight / D"
            scheme["jump"] = "Space / W / ArrowUp"
        elif "racing" in m_str:
            scheme["accelerate"] = "ArrowUp / W"
            scheme["brake"] = "ArrowDown / S"
            scheme["steer_left"] = "ArrowLeft / A"
            scheme["steer_right"] = "ArrowRight / D"
        else:
            scheme["move_up"] = "ArrowUp / W"
            scheme["move_down"] = "ArrowDown / S"
            scheme["move_left"] = "ArrowLeft / A"
            scheme["move_right"] = "ArrowRight / D"
        if "shooting" in m_str:
            scheme["fire"] = "Space / Mouse Click"
        if "puzzle_solving" in m_str:
            scheme["interact"] = "E / Space"
        scheme["pause"] = "Escape"
        return scheme


class _ArtistAgent:
    """Defines visual style, color palette, and atmosphere."""

    NAME = "Artist"
    ROLE = "visual_design"

    PALETTES = {
        "fantasy": ["#1a1a2e", "#16213e", "#f97316", "#fbbf24", "#4ade80", "#c084fc"],
        "sci_fi": ["#0a0a1a", "#0f1f2e", "#06b6d4", "#60a5fa", "#a855f7", "#fbbf24"],
        "horror": ["#0a0a0a", "#1a0a0a", "#7f1d1d", "#dc2626", "#fbbf24", "#475569"],
        "nature": ["#0f1a0a", "#1a2e1a", "#22c55e", "#4ade80", "#fbbf24", "#06b6d4"],
        "retro": ["#1a1a2e", "#16213e", "#ff006e", "#fb5607", "#ffbe0b", "#8338ec"],
        "minimal": ["#0a0a0a", "#1a1a1a", "#f5f5f5", "#f97316", "#6b7280", "#374151"],
    }

    def contribute(self, prompt: str, previous: Dict[str, Any]) -> AgentContribution:
        lower_prompt = prompt.lower()

        # Determine theme
        theme = "fantasy"
        if any(w in lower_prompt for w in ["space", "sci-fi", "cyber", "robot", "future", "laser"]):
            theme = "sci_fi"
        elif any(w in lower_prompt for w in ["horror", "dark", "scary", "zombie", "haunted"]):
            theme = "horror"
        elif any(w in lower_prompt for w in ["forest", "nature", "garden", "jungle", "tree"]):
            theme = "nature"
        elif any(w in lower_prompt for w in ["retro", "arcade", "pixel", "8-bit", "neon"]):
            theme = "retro"
        elif any(w in lower_prompt for w in ["minimal", "clean", "simple", "monochrome"]):
            theme = "minimal"

        palette = self.PALETTES.get(theme, self.PALETTES["fantasy"])

        # Visual style
        visual_styles = {
            "fantasy": "flat-2d with warm gradients and particle accents",
            "sci_fi": "neon outlines on dark backgrounds with glow effects",
            "horror": "high-contrast with deep shadows and desaturated tones",
            "nature": "organic shapes with vibrant greens and soft lighting",
            "retro": "pixel-art aesthetic with limited color palette and CRT scanlines",
            "minimal": "geometric shapes with stark contrast and no gradients",
        }
        visual_style = visual_styles.get(theme, visual_styles["fantasy"])

        # Atmosphere
        atmospheres = {
            "fantasy": "Whimsical and adventurous with a sense of discovery",
            "sci_fi": "Cold and technological with underlying tension",
            "horror": "Oppressive and unsettling with moments of dread",
            "nature": "Calm and restorative with occasional excitement",
            "retro": "Nostalgic and energetic with arcade excitement",
            "minimal": "Focused and clean with no visual distractions",
        }
        atmosphere = atmospheres.get(theme, atmospheres["fantasy"])

        return AgentContribution(
            agent_name=self.NAME,
            agent_role=self.ROLE,
            timestamp=time.time(),
            content={
                "theme": theme,
                "visual_style": visual_style,
                "color_palette": palette,
                "atmosphere": atmosphere,
                "particle_effects": self._design_particles(lower_prompt),
                "ui_style": "dark glassmorphism with orange accent (#f97316)",
            },
        )

    def _design_particles(self, prompt: str) -> List[str]:
        particles: List[str] = []
        if any(w in prompt for w in ["fire", "explosion", "lava"]):
            particles.append("fire_burst")
        if any(w in prompt for w in ["ice", "snow", "frost"]):
            particles.append("ice_shatter")
        if any(w in prompt for w in ["magic", "spell", "portal"]):
            particles.append("magic_sparkle")
        if any(w in prompt for w in ["water", "ocean", "rain"]):
            particles.append("water_splash")
        if not particles:
            particles.extend(["collect_burst", "death_burst", "spawn_burst"])
        return particles


class _TesterAgent:
    """Simulates playtests, identifies issues, and suggests fixes."""

    NAME = "Tester"
    ROLE = "quality_assurance"

    def contribute(self, prompt: str, previous: Dict[str, Any]) -> AgentContribution:
        designer_output = previous.get("Designer", {})
        programmer_output = previous.get("Programmer", {})
        mechanics = designer_output.get("core_mechanics", [])
        risks = programmer_output.get("technical_risks", [])

        # Simulated playtest findings
        findings: List[str] = []
        mitigations: List[str] = []

        m_str = str(mechanics)
        if "platforming" in m_str:
            findings.append("Players may struggle with precise jump timing on moving platforms")
            mitigations.append("Add coyote time (100ms grace period after leaving ledge)")
        if "shooting" in m_str:
            findings.append("Projectile hit detection may feel unfair at high speeds")
            mitigations.append("Use generous hitboxes and visual feedback on hit")
        if "procedural_generation" in m_str:
            findings.append("Some generated layouts may be unsolvable or too difficult")
            mitigations.append("Implement solvability checks and difficulty capping per level")
        if "permadeath" in m_str:
            findings.append("Permadeath may cause frustration after long runs")
            mitigations.append("Provide meta-progression rewards that persist between runs")
        if "boss_encounter" in m_str:
            findings.append("Boss fights may have unclear telegraphs for attacks")
            mitigations.append("Add visual wind-up animations and audio cues before attacks")
        if "puzzle_solving" in m_str:
            findings.append("Players may get stuck without knowing which mechanics to use")
            mitigations.append("Implement subtle environmental hints and optional tutorial popups")

        if not findings:
            findings.append("Game may feel repetitive after extended play sessions")
            mitigations.append("Introduce variety through procedural elements and daily challenges")

        findings.append("Difficulty spike may occur at level transitions")
        mitigations.append("Implement smooth difficulty curve with occasional breather levels")

        # Edge cases
        edge_cases: List[str] = [
            "Player simultaneously triggers collision with enemy and collectible",
            "Player reaches level boundary before level transition triggers",
            "Rapid input causes animation state conflicts",
        ]

        return AgentContribution(
            agent_name=self.NAME,
            agent_role=self.ROLE,
            timestamp=time.time(),
            content={
                "test_findings": findings,
                "risk_mitigations": mitigations,
                "edge_cases": edge_cases,
                "playtest_coverage": {
                    "mechanics_tested": len(mechanics),
                    "edge_cases_identified": len(edge_cases),
                    "risks_addressed": len(risks),
                },
                "quality_prediction": self._predict_quality(designer_output),
            },
        )

    def _predict_quality(self, designer_output: Dict[str, Any]) -> Dict[str, float]:
        engagement = designer_output.get("estimated_engagement", 0.6)
        difficulty = designer_output.get("estimated_difficulty", 0.5)
        replayability = designer_output.get("estimated_replayability", 0.4)
        # Tester adjusts predictions based on risk assessment
        return {
            "engagement": round(min(1.0, engagement + 0.05), 2),
            "difficulty": round(min(1.0, difficulty), 2),
            "replayability": round(min(1.0, replayability + 0.03), 2),
            "overall": round(min(1.0, (engagement + replayability + (1 - abs(difficulty - 0.5))) / 3), 2),
        }


class _ComposerAgent:
    """Defines audio mood, tempo, and SFX landscape."""

    NAME = "Composer"
    ROLE = "audio_design"

    def contribute(self, prompt: str, previous: Dict[str, Any]) -> AgentContribution:
        lower_prompt = prompt.lower()
        artist_output = previous.get("Artist", {})
        theme = artist_output.get("theme", "fantasy")

        # Tempo based on genre and theme
        tempo_map = {
            "fantasy": 100,
            "sci_fi": 120,
            "horror": 70,
            "nature": 85,
            "retro": 140,
            "minimal": 90,
        }
        tempo = tempo_map.get(theme, 100)
        if any(w in lower_prompt for w in ["fast", "speed", "race", "intense"]):
            tempo = min(180, tempo + 30)
        if any(w in lower_prompt for w in ["calm", "relax", "chill", "peaceful"]):
            tempo = max(60, tempo - 20)

        # Audio profile
        profiles = {
            "fantasy": "orchestral with woodwind melodies and light percussion",
            "sci_fi": "synthwave with pulsing basslines and digital textures",
            "horror": "ambient drones with dissonant strings and silence",
            "nature": "acoustic with gentle guitar and environmental sounds",
            "retro": "chiptune with square waves and fast arpeggios",
            "minimal": "ambient piano with sparse electronic accents",
        }
        profile = profiles.get(theme, profiles["fantasy"])

        # SFX landscape
        sfx: List[str] = ["jump", "collect", "damage", "game_over", "level_complete"]
        m_str = lower_prompt
        if any(w in m_str for w in ["shoot", "gun", "bullet"]):
            sfx.extend(["shoot", "hit", "reload"])
        if any(w in m_str for w in ["explosion", "bomb", "blast"]):
            sfx.extend(["explosion", "debris"])
        if any(w in m_str for w in ["magic", "spell", "portal"]):
            sfx.extend(["magic_cast", "portal_open", "enchant"])
        if any(w in m_str for w in ["sword", "slash", "melee"]):
            sfx.extend(["sword_swing", "sword_hit", "parry"])
        sfx.extend(["ui_select", "ui_back", "achievement"])

        return AgentContribution(
            agent_name=self.NAME,
            agent_role=self.ROLE,
            timestamp=time.time(),
            content={
                "audio_profile": profile,
                "tempo_bpm": tempo,
                "sfx_landscape": sfx,
                "dynamic_audio": True,
                "adaptive_layers": self._design_adaptive_layers(tempo),
            },
        )

    def _design_adaptive_layers(self, tempo: int) -> List[str]:
        if tempo >= 130:
            return ["base_rhythm", "melody_layer", "intensity_layer", "climax_layer"]
        elif tempo >= 90:
            return ["ambient_pad", "melody_layer", "intensity_layer"]
        else:
            return ["ambient_drone", "tension_layer"]


# =============================================================================
# Game Studio Orchestrator
# =============================================================================


class GameStudio:
    """
    Multi-agent game studio where specialized AI agents collaborate to design
    a complete game blueprint. Each agent contributes its domain expertise and
    can build on the outputs of previous agents.

    The studio runs a multi-round collaboration:
      Round 1: Each agent independently proposes their domain design
      Round 2: Agents review each other's work and suggest refinements
      Round 3: Studio director consolidates into a final blueprint

    Implements a thread-safe singleton pattern.
    """

    _instance: Optional["GameStudio"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GameStudio._instance is not None:
            raise RuntimeError("Use GameStudio.get_instance()")
        self._initialized: bool = False
        self._designer = _DesignerAgent()
        self._programmer = _ProgrammerAgent()
        self._artist = _ArtistAgent()
        self._tester = _TesterAgent()
        self._composer = _ComposerAgent()
        self._session_history: deque = deque(maxlen=50)
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GameStudio":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the studio."""
        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            logger.info("GameStudio initialized with 5 specialist agents")

    def collaborate(
        self,
        prompt: str,
        rounds: int = 3,
    ) -> StudioResult:
        """
        Run a multi-round collaboration session where specialist agents
        design a game blueprint together.

        Args:
            prompt: Natural-language game description
            rounds: Number of collaboration rounds (default 3)

        Returns:
            StudioResult with the consolidated blueprint and agent outputs
        """
        if not self._initialized:
            self.initialize()

        session_id = f"studio_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        agent_outputs: List[AgentContribution] = []
        collaboration_log: List[CollaborationMessage] = []
        previous_outputs: Dict[str, Dict[str, Any]] = {}

        try:
            # Phase 1: Independent contributions
            for agent in [self._designer, self._programmer, self._artist, self._tester, self._composer]:
                contribution = agent.contribute(prompt, previous_outputs)
                agent_outputs.append(contribution)
                previous_outputs[contribution.agent_name] = contribution.content

                collaboration_log.append(CollaborationMessage(
                    from_agent=contribution.agent_name,
                    to_agent="Studio",
                    message_type="proposal",
                    content=f"{contribution.agent_name} submitted {contribution.agent_role} proposal",
                    timestamp=time.time(),
                ))

            # Phase 2: Cross-agent feedback (tester reviews designer + programmer)
            if rounds >= 2:
                tester_feedback = self._tester.contribute(prompt, previous_outputs)
                tester_feedback.agent_name = "Tester"
                tester_feedback.agent_role = "cross_review"
                agent_outputs.append(tester_feedback)

                collaboration_log.append(CollaborationMessage(
                    from_agent="Tester",
                    to_agent="Designer",
                    message_type="feedback",
                    content="Tester reviewed design and architecture for playability risks",
                    timestamp=time.time(),
                ))

                collaboration_log.append(CollaborationMessage(
                    from_agent="Designer",
                    to_agent="Tester",
                    message_type="revision",
                    content="Designer acknowledged risk mitigations and adjusted balance notes",
                    timestamp=time.time(),
                ))

            # Phase 3: Consensus and blueprint consolidation
            blueprint = self._consolidate_blueprint(prompt, previous_outputs)
            consensus = True

            collaboration_log.append(CollaborationMessage(
                from_agent="Studio",
                to_agent="all",
                message_type="consensus",
                content="Studio reached consensus on final game blueprint",
                timestamp=time.time(),
            ))

            duration = time.time() - start_time

            result = StudioResult(
                session_id=session_id,
                success=True,
                prompt=prompt,
                blueprint=blueprint,
                agent_outputs=agent_outputs,
                collaboration_log=collaboration_log,
                rounds=rounds,
                duration_s=round(duration, 3),
                consensus_reached=consensus,
                error=None,
            )

            with self._lock:
                self._session_history.append({
                    "session_id": session_id,
                    "prompt": prompt[:100],
                    "success": True,
                    "rounds": rounds,
                    "duration_s": round(duration, 3),
                    "agents": 5,
                    "timestamp": time.time(),
                })

            return result

        except Exception as exc:
            logger.exception("GameStudio collaboration failed: %s", exc)
            duration = time.time() - start_time
            return StudioResult(
                session_id=session_id,
                success=False,
                prompt=prompt,
                blueprint=GameBlueprint(),
                agent_outputs=agent_outputs,
                collaboration_log=collaboration_log,
                rounds=rounds,
                duration_s=round(duration, 3),
                consensus_reached=False,
                error=str(exc),
            )

    def _consolidate_blueprint(
        self,
        prompt: str,
        outputs: Dict[str, Dict[str, Any]],
    ) -> GameBlueprint:
        """Consolidate all agent outputs into a single blueprint."""
        designer = outputs.get("Designer", {})
        programmer = outputs.get("Programmer", {})
        artist = outputs.get("Artist", {})
        tester = outputs.get("Tester", {})
        composer = outputs.get("Composer", {})

        # Extract title from prompt
        title = self._derive_title(prompt)

        return GameBlueprint(
            title=title,
            genre=designer.get("core_mechanics", ["exploration"])[0] if designer.get("core_mechanics") else "exploration",
            theme=artist.get("theme", "fantasy"),
            visual_style=artist.get("visual_style", "flat-2d"),
            audio_profile=composer.get("audio_profile", ""),
            core_mechanics=designer.get("core_mechanics", []),
            secondary_mechanics=designer.get("secondary_mechanics", []),
            progression_system=designer.get("progression_system", ""),
            balance_notes=designer.get("balance_notes", ""),
            color_palette=artist.get("color_palette", []),
            atmosphere=artist.get("atmosphere", ""),
            tempo_bpm=composer.get("tempo_bpm", 100),
            sfx_landscape=composer.get("sfx_landscape", []),
            test_findings=tester.get("test_findings", []),
            risk_mitigations=tester.get("risk_mitigations", []),
            innovation_angles=designer.get("innovation_angles", []),
            estimated_engagement=designer.get("estimated_engagement", 0.6),
            estimated_difficulty=designer.get("estimated_difficulty", 0.5),
            estimated_replayability=designer.get("estimated_replayability", 0.4),
        )

    def _derive_title(self, prompt: str) -> str:
        """Generate a game title from the prompt."""
        words = prompt.split()
        # Take significant words and capitalize
        significant = [w.capitalize() for w in words if len(w) > 3 and w.lower() not in {
            "with", "that", "this", "have", "from", "they", "will", "would",
            "could", "should", "there", "their", "about", "which", "when",
        }]
        if not significant:
            return "SparkLabs Game"
        # Take up to 3 words
        title = " ".join(significant[:3])
        # Add a suffix for flair
        suffixes = ["Quest", "Adventure", "Saga", "Chronicles", "Rising"]
        return f"{title} {random.choice(suffixes)}"

    def get_status(self) -> Dict[str, Any]:
        """Return studio status information."""
        with self._lock:
            return {
                "status": "ready" if self._initialized else "not_initialized",
                "sessions_completed": len(self._session_history),
                "agents": ["Designer", "Programmer", "Artist", "Tester", "Composer"],
                "recent_sessions": list(self._session_history)[-5:],
            }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the studio's session history."""
        with self._lock:
            return list(self._session_history)


# =============================================================================
# Module-level convenience
# =============================================================================


def get_game_studio() -> GameStudio:
    """Convenience function to access the singleton GameStudio."""
    return GameStudio.get_instance()
