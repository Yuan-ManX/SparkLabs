"""
SparkLabs Agent - Creative Director

An autonomous creative direction system for game projects. Generates
creative briefs, gameplay pillars, art direction guidelines, mood
boards, and narrative themes. Coordinates creative vision across
game design, visual style, audio direction, and player experience
to produce cohesive, compelling game concepts.

Core capabilities:
  - Creative brief generation with project scope and constraints
  - Gameplay pillar definition (core mechanics, feel, uniqueness)
  - Art direction synthesis (color palettes, visual style, UI tone)
  - Mood board compilation with thematic descriptors
  - Narrative theme exploration and tone analysis
  - Audio direction guidance (soundtrack mood, SFX style)
  - Player experience mapping (emotional journey, engagement curve)
  - Creative constraint satisfaction (genre rules, scope limits)

Architecture:
  AgentCreativeDirector (Singleton)
    |-- CreativeBrief (dataclass)
    |-- GameplayPillar (dataclass)
    |-- ArtDirectionProfile (dataclass)
    |-- MoodDescriptor (dataclass)
    |-- NarrativeTheme (dataclass)
    |-- AudioDirection (dataclass)
    |-- PlayerExperienceMap (dataclass)
    |-- generate_creative_brief()
    |-- define_gameplay_pillars()
    |-- synthesize_art_direction()
    |-- compile_mood_board()
    |-- explore_narrative_themes()
    |-- design_audio_direction()
    |-- map_player_experience()
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class GenreCategory(Enum):
    ACTION = "action"
    ADVENTURE = "adventure"
    RPG = "rpg"
    STRATEGY = "strategy"
    SIMULATION = "simulation"
    PUZZLE = "puzzle"
    PLATFORMER = "platformer"
    SHOOTER = "shooter"
    SURVIVAL = "survival"
    ROGUELIKE = "roguelike"
    METROIDVANIA = "metroidvania"
    HORROR = "horror"
    VISUAL_NOVEL = "visual_novel"
    RACING = "racing"
    SPORTS = "sports"
    FIGHTING = "fighting"
    RHYTHM = "rhythm"
    STEALTH = "stealth"
    SANDBOX = "sandbox"


class VisualStyle(Enum):
    PIXEL_ART = "pixel_art"
    LOW_POLY = "low_poly"
    STYLIZED = "stylized"
    REALISTIC = "realistic"
    CEL_SHADED = "cel_shaded"
    HAND_DRAWN = "hand_drawn"
    MINIMALIST = "minimalist"
    VOXEL = "voxel"
    ISOMETRIC = "isometric"
    RETRO = "retro"
    PHOTOREAL = "photoreal"
    ABSTRACT = "abstract"


class EmotionalTone(Enum):
    HOPEFUL = "hopeful"
    MYSTERIOUS = "mysterious"
    TENSE = "tense"
    JOYFUL = "joyful"
    MELANCHOLIC = "melancholic"
    EPIC = "epic"
    WHIMSICAL = "whimsical"
    DARK = "dark"
    SERENE = "serene"
    CHAOTIC = "chaotic"
    NOSTALGIC = "nostalgic"
    UNSETTLING = "unsettling"


class TargetAudience(Enum):
    CASUAL = "casual"
    CORE = "core"
    HARDCORE = "hardcore"
    FAMILY = "family"
    INDIE = "indie"
    COMPETITIVE = "competitive"
    COZY = "cozy"
    EDUCATIONAL = "educational"


@dataclass
class CreativeBrief:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    project_name: str = ""
    tagline: str = ""
    genre: GenreCategory = GenreCategory.ADVENTURE
    sub_genres: List[str] = field(default_factory=list)
    target_audience: TargetAudience = TargetAudience.CORE
    visual_style: VisualStyle = VisualStyle.STYLIZED
    emotional_tone: EmotionalTone = EmotionalTone.HOPEFUL
    scope_description: str = ""
    unique_selling_points: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    inspiration_keywords: List[str] = field(default_factory=list)
    estimated_playtime_hours: float = 5.0
    target_platforms: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "tagline": self.tagline,
            "genre": self.genre.value,
            "sub_genres": self.sub_genres,
            "target_audience": self.target_audience.value,
            "visual_style": self.visual_style.value,
            "emotional_tone": self.emotional_tone.value,
            "scope_description": self.scope_description,
            "unique_selling_points": self.unique_selling_points,
            "constraints": self.constraints,
            "inspiration_keywords": self.inspiration_keywords,
            "estimated_playtime_hours": self.estimated_playtime_hours,
            "target_platforms": self.target_platforms,
            "created_at": self.created_at,
        }


@dataclass
class GameplayPillar:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    core_mechanic: str = ""
    skill_expression: str = ""
    novelty_factor: float = 0.5
    depth_score: float = 0.5
    accessibility_score: float = 0.5
    synergy_with_pillars: List[str] = field(default_factory=list)
    example_moments: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "core_mechanic": self.core_mechanic,
            "skill_expression": self.skill_expression,
            "novelty_factor": self.novelty_factor,
            "depth_score": self.depth_score,
            "accessibility_score": self.accessibility_score,
            "synergy_with_pillars": self.synergy_with_pillars,
            "example_moments": self.example_moments,
            "created_at": self.created_at,
        }


@dataclass
class ArtDirectionProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    style: VisualStyle = VisualStyle.STYLIZED
    primary_palette: List[str] = field(default_factory=list)
    secondary_palette: List[str] = field(default_factory=list)
    accent_palette: List[str] = field(default_factory=list)
    background_palette: List[str] = field(default_factory=list)
    ui_font_family: str = "Inter"
    ui_roundness: float = 0.5
    character_proportions: str = "realistic"
    environment_density: str = "moderate"
    lighting_approach: str = "dynamic"
    post_processing_style: str = "subtle"
    reference_descriptors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "style": self.style.value,
            "primary_palette": self.primary_palette,
            "secondary_palette": self.secondary_palette,
            "accent_palette": self.accent_palette,
            "background_palette": self.background_palette,
            "ui_font_family": self.ui_font_family,
            "ui_roundness": self.ui_roundness,
            "character_proportions": self.character_proportions,
            "environment_density": self.environment_density,
            "lighting_approach": self.lighting_approach,
            "post_processing_style": self.post_processing_style,
            "reference_descriptors": self.reference_descriptors,
            "created_at": self.created_at,
        }


@dataclass
class MoodDescriptor:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    color_temperature: str = "warm"
    saturation_level: float = 0.5
    contrast_level: float = 0.5
    associated_emotions: List[str] = field(default_factory=list)
    visual_motifs: List[str] = field(default_factory=list)
    audio_motifs: List[str] = field(default_factory=list)
    scene_examples: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color_temperature": self.color_temperature,
            "saturation_level": self.saturation_level,
            "contrast_level": self.contrast_level,
            "associated_emotions": self.associated_emotions,
            "visual_motifs": self.visual_motifs,
            "audio_motifs": self.audio_motifs,
            "scene_examples": self.scene_examples,
            "created_at": self.created_at,
        }


@dataclass
class NarrativeTheme:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    central_conflict: str = ""
    protagonist_archetype: str = ""
    antagonist_archetype: str = ""
    story_structure: str = "three_act"
    core_message: str = ""
    world_building_hooks: List[str] = field(default_factory=list)
    character_relationships: List[Dict[str, str]] = field(default_factory=list)
    branching_opportunities: List[str] = field(default_factory=list)
    emotional_beats: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "central_conflict": self.central_conflict,
            "protagonist_archetype": self.protagonist_archetype,
            "antagonist_archetype": self.antagonist_archetype,
            "story_structure": self.story_structure,
            "core_message": self.core_message,
            "world_building_hooks": self.world_building_hooks,
            "character_relationships": self.character_relationships,
            "branching_opportunities": self.branching_opportunities,
            "emotional_beats": self.emotional_beats,
            "created_at": self.created_at,
        }


@dataclass
class AudioDirection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    soundtrack_genre: str = ""
    instrumentation: List[str] = field(default_factory=list)
    tempo_range: Tuple[float, float] = (80.0, 140.0)
    dynamic_range: str = "moderate"
    leitmotif_themes: List[str] = field(default_factory=list)
    ambient_style: str = "natural"
    sfx_design_approach: str = "stylized"
    voice_direction: str = "naturalistic"
    silence_usage: str = "strategic"
    audio_priority_hierarchy: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "soundtrack_genre": self.soundtrack_genre,
            "instrumentation": self.instrumentation,
            "tempo_range": list(self.tempo_range),
            "dynamic_range": self.dynamic_range,
            "leitmotif_themes": self.leitmotif_themes,
            "ambient_style": self.ambient_style,
            "sfx_design_approach": self.sfx_design_approach,
            "voice_direction": self.voice_direction,
            "silence_usage": self.silence_usage,
            "audio_priority_hierarchy": self.audio_priority_hierarchy,
            "created_at": self.created_at,
        }


@dataclass
class PlayerExperienceMap:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    emotional_journey: List[Dict[str, Any]] = field(default_factory=list)
    engagement_curve: List[float] = field(default_factory=list)
    key_moments: List[Dict[str, str]] = field(default_factory=list)
    difficulty_progression: str = "gradual"
    learning_curve_steepness: float = 0.5
    replayability_factors: List[str] = field(default_factory=list)
    social_experience: str = "solo"
    accessibility_features: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "emotional_journey": self.emotional_journey,
            "engagement_curve": self.engagement_curve,
            "key_moments": self.key_moments,
            "difficulty_progression": self.difficulty_progression,
            "learning_curve_steepness": self.learning_curve_steepness,
            "replayability_factors": self.replayability_factors,
            "social_experience": self.social_experience,
            "accessibility_features": self.accessibility_features,
            "created_at": self.created_at,
        }


_GENRE_PILLAR_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "action": [
        {"name": "Combat Flow", "mechanic": "Responsive melee combat with combo chaining",
         "skill": "Timing, positioning, and resource management"},
        {"name": "Mobility", "mechanic": "Fluid movement with dashing, wall-running, and aerial control",
         "skill": "Spatial awareness and execution precision"},
        {"name": "Power Fantasy", "mechanic": "Escalating abilities with satisfying visual and audio feedback",
         "skill": "Build optimization and ability synergy"},
    ],
    "rpg": [
        {"name": "Character Progression", "mechanic": "Deep skill trees with meaningful branching choices",
         "skill": "Strategic planning and specialization"},
        {"name": "World Interaction", "mechanic": "Reactive NPCs, environmental storytelling, and faction systems",
         "skill": "Social navigation and consequence management"},
        {"name": "Build Expression", "mechanic": "Equipment, abilities, and stats that create unique playstyles",
         "skill": "System mastery and theorycrafting"},
    ],
    "puzzle": [
        {"name": "Mental Model Building", "mechanic": "Gradually introduced mechanics that combine in novel ways",
         "skill": "Pattern recognition and logical deduction"},
        {"name": "Environmental Manipulation", "mechanic": "Physics-based interactions with the game world",
         "skill": "Spatial reasoning and creative problem-solving"},
        {"name": "Discovery Satisfaction", "mechanic": "Hidden connections and elegant solutions with 'aha' moments",
         "skill": "Persistence and lateral thinking"},
    ],
    "survival": [
        {"name": "Resource Tension", "mechanic": "Meaningful scarcity that creates constant decision pressure",
         "skill": "Prioritization and risk assessment"},
        {"name": "Environmental Mastery", "mechanic": "Learned adaptation to procedurally generated challenges",
         "skill": "Observation and adaptation"},
        {"name": "Progression Through Knowledge", "mechanic": "Player knowledge growth as primary advancement",
         "skill": "Learning through failure and experimentation"},
    ],
}

_STYLE_PALETTES: Dict[str, Dict[str, List[str]]] = {
    "pixel_art": {
        "primary": ["#2b1d38", "#5a3d7a", "#8b5fbf"],
        "secondary": ["#e8a838", "#f0d088", "#d84040"],
        "accent": ["#40e0d0", "#48d1cc", "#20b2aa"],
        "background": ["#1a1028", "#2a1a3a", "#3a2a4c"],
    },
    "stylized": {
        "primary": ["#1a1a2e", "#16213e", "#0f3460"],
        "secondary": ["#e94560", "#ff6b6b", "#f8b500"],
        "accent": ["#00d2ff", "#00b4d8", "#0096c7"],
        "background": ["#0a0a1a", "#12122a", "#1a1a3e"],
    },
    "cel_shaded": {
        "primary": ["#264653", "#2a9d8f", "#e9c46a"],
        "secondary": ["#f4a261", "#e76f51", "#e63946"],
        "accent": ["#f1faee", "#a8dadc", "#457b9d"],
        "background": ["#1d3557", "#1a2f4a", "#12263a"],
    },
}

_MOOD_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "epic_adventure": {
        "color_temperature": "warm",
        "saturation_level": 0.7,
        "contrast_level": 0.8,
        "emotions": ["wonder", "excitement", "determination"],
        "visual_motifs": ["grand landscapes", "ancient ruins", "celestial bodies"],
        "audio_motifs": ["orchestral swells", "heroic brass", "rolling percussion"],
    },
    "mysterious_exploration": {
        "color_temperature": "cool",
        "saturation_level": 0.4,
        "contrast_level": 0.6,
        "emotions": ["curiosity", "tension", "anticipation"],
        "visual_motifs": ["fog-shrouded paths", "flickering lights", "abandoned structures"],
        "audio_motifs": ["ambient drones", "distant echoes", "subtle chimes"],
    },
    "cozy_comfort": {
        "color_temperature": "warm",
        "saturation_level": 0.5,
        "contrast_level": 0.3,
        "emotions": ["comfort", "peace", "belonging"],
        "visual_motifs": ["soft lighting", "rounded shapes", "natural materials"],
        "audio_motifs": ["acoustic guitar", "gentle piano", "nature sounds"],
    },
}


class AgentCreativeDirector:
    _instance: Optional["AgentCreativeDirector"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentCreativeDirector":
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
        self._briefs: Dict[str, CreativeBrief] = {}
        self._pillars: Dict[str, GameplayPillar] = {}
        self._art_profiles: Dict[str, ArtDirectionProfile] = {}
        self._moods: Dict[str, MoodDescriptor] = {}
        self._themes: Dict[str, NarrativeTheme] = {}
        self._audio_directions: Dict[str, AudioDirection] = {}
        self._experience_maps: Dict[str, PlayerExperienceMap] = {}
        self._total_briefs_generated: int = 0
        self._total_pillars_defined: int = 0
        self._total_art_profiles: int = 0

    def generate_creative_brief(
        self,
        project_name: str,
        genre: Optional[str] = None,
        target_audience: Optional[str] = None,
        visual_style: Optional[str] = None,
        emotional_tone: Optional[str] = None,
    ) -> CreativeBrief:
        genre_enum = GenreCategory(genre) if genre else GenreCategory.ADVENTURE
        audience_enum = TargetAudience(target_audience) if target_audience else TargetAudience.CORE
        style_enum = VisualStyle(visual_style) if visual_style else VisualStyle.STYLIZED
        tone_enum = EmotionalTone(emotional_tone) if emotional_tone else EmotionalTone.HOPEFUL

        taglines = {
            GenreCategory.ADVENTURE: "A journey that redefines discovery",
            GenreCategory.RPG: "Every choice writes your legend",
            GenreCategory.PUZZLE: "Where logic meets creativity",
            GenreCategory.ACTION: "Precision is your greatest weapon",
            GenreCategory.SURVIVAL: "Adapt or be forgotten",
        }

        scope_descriptions = {
            TargetAudience.CASUAL: "Accessible, pick-up-and-play design with clear objectives and gentle difficulty",
            TargetAudience.CORE: "Balanced depth with approachable systems that reward mastery",
            TargetAudience.HARDCORE: "Challenging mechanics with high skill ceilings and complex systems",
        }

        brief = CreativeBrief(
            project_name=project_name,
            tagline=taglines.get(genre_enum, "Where imagination meets play"),
            genre=genre_enum,
            target_audience=audience_enum,
            visual_style=style_enum,
            emotional_tone=tone_enum,
            scope_description=scope_descriptions.get(
                audience_enum, "A carefully crafted experience with clear creative vision"
            ),
        )

        self._briefs[brief.id] = brief
        self._total_briefs_generated += 1
        return brief

    def define_gameplay_pillars(
        self,
        brief_id: str,
        custom_pillars: Optional[List[Dict[str, str]]] = None,
    ) -> List[GameplayPillar]:
        brief = self._briefs.get(brief_id)
        if not brief:
            raise ValueError(f"Creative brief '{brief_id}' not found")

        templates = _GENRE_PILLAR_TEMPLATES.get(brief.genre.value, [])
        pillars_to_use = custom_pillars if custom_pillars else templates

        pillars = []
        for i, pillar_data in enumerate(pillars_to_use):
            if isinstance(pillar_data, dict):
                pillar = GameplayPillar(
                    name=pillar_data.get("name", f"Pillar {i+1}"),
                    description=pillar_data.get("description", ""),
                    core_mechanic=pillar_data.get("mechanic", pillar_data.get("core_mechanic", "")),
                    skill_expression=pillar_data.get("skill", pillar_data.get("skill_expression", "")),
                    novelty_factor=0.5 + i * 0.1,
                    depth_score=0.5 + i * 0.08,
                    accessibility_score=0.7 - i * 0.1,
                )
                pillars.append(pillar)
                self._pillars[pillar.id] = pillar
                self._total_pillars_defined += 1

        return pillars

    def synthesize_art_direction(
        self,
        brief_id: str,
        style_override: Optional[str] = None,
    ) -> ArtDirectionProfile:
        brief = self._briefs.get(brief_id)
        if not brief:
            raise ValueError(f"Creative brief '{brief_id}' not found")

        style_key = style_override or brief.visual_style.value
        palettes = _STYLE_PALETTES.get(style_key, _STYLE_PALETTES["stylized"])

        lightning_by_tone = {
            EmotionalTone.DARK: "low_key",
            EmotionalTone.HOPEFUL: "bright",
            EmotionalTone.MYSTERIOUS: "atmospheric",
            EmotionalTone.TENSE: "high_contrast",
            EmotionalTone.EPIC: "dramatic",
        }

        profile = ArtDirectionProfile(
            style=VisualStyle(style_key) if style_key in [s.value for s in VisualStyle] else VisualStyle.STYLIZED,
            primary_palette=palettes["primary"],
            secondary_palette=palettes["secondary"],
            accent_palette=palettes["accent"],
            background_palette=palettes["background"],
            ui_font_family="Inter" if brief.visual_style != VisualStyle.PIXEL_ART else "Press Start 2P",
            ui_roundness=0.6 if brief.visual_style == VisualStyle.STYLIZED else 0.2,
            character_proportions="stylized" if brief.visual_style == VisualStyle.STYLIZED else "realistic",
            environment_density="dense" if brief.visual_style == VisualStyle.REALISTIC else "moderate",
            lighting_approach=lightning_by_tone.get(brief.emotional_tone, "dynamic"),
            post_processing_style="cinematic" if brief.emotional_tone == EmotionalTone.EPIC else "subtle",
        )

        self._art_profiles[profile.id] = profile
        self._total_art_profiles += 1
        return profile

    def compile_mood_board(
        self,
        brief_id: str,
        mood_name: Optional[str] = None,
    ) -> List[MoodDescriptor]:
        brief = self._briefs.get(brief_id)
        if not brief:
            raise ValueError(f"Creative brief '{brief_id}' not found")

        moods = []

        tone_to_mood = {
            EmotionalTone.HOPEFUL: "epic_adventure",
            EmotionalTone.MYSTERIOUS: "mysterious_exploration",
            EmotionalTone.TENSE: "mysterious_exploration",
            EmotionalTone.DARK: "mysterious_exploration",
        }
        mood_key = mood_name or tone_to_mood.get(brief.emotional_tone, "epic_adventure")
        template = _MOOD_TEMPLATES.get(mood_key, _MOOD_TEMPLATES["epic_adventure"])

        descriptor = MoodDescriptor(
            name=mood_key,
            description=f"A {mood_key.replace('_', ' ')} mood for {brief.project_name}",
            color_temperature=template["color_temperature"],
            saturation_level=template["saturation_level"],
            contrast_level=template["contrast_level"],
            associated_emotions=template["emotions"],
            visual_motifs=template["visual_motifs"],
            audio_motifs=template["audio_motifs"],
        )
        moods.append(descriptor)
        self._moods[descriptor.id] = descriptor

        secondary_mood = MoodDescriptor(
            name=f"{mood_key}_contrast",
            description=f"A contrasting mood to create dynamic range for {brief.project_name}",
            color_temperature="cool" if template["color_temperature"] == "warm" else "warm",
            saturation_level=1.0 - template["saturation_level"],
            contrast_level=template["contrast_level"],
            associated_emotions=["reflection", "relief", "surprise"],
            visual_motifs=["contrasting spaces", "quiet moments", "transitional areas"],
            audio_motifs=["ambient silence", "solo instruments", "reverb spaces"],
        )
        moods.append(secondary_mood)
        self._moods[secondary_mood.id] = secondary_mood

        return moods

    def explore_narrative_themes(
        self,
        brief_id: str,
        central_conflict: str = "",
        protagonist_archetype: str = "",
    ) -> NarrativeTheme:
        brief = self._briefs.get(brief_id)
        if not brief:
            raise ValueError(f"Creative brief '{brief_id}' not found")

        archetypes_by_tone = {
            EmotionalTone.HOPEFUL: ("reluctant_hero", "corrupt_institution"),
            EmotionalTone.DARK: ("anti_hero", "internal_demon"),
            EmotionalTone.MYSTERIOUS: ("detective_seeker", "hidden_truth"),
            EmotionalTone.EPIC: ("chosen_one", "ancient_evil"),
        }

        protag, antag = archetypes_by_tone.get(
            brief.emotional_tone, ("everyman_hero", "overwhelming_odds")
        )

        theme = NarrativeTheme(
            name=f"{brief.project_name}_theme",
            central_conflict=central_conflict or f"A personal journey in a world shaped by choices",
            protagonist_archetype=protagonist_archetype or protag,
            antagonist_archetype=antag,
            story_structure="three_act",
            core_message="The choices we make define who we become",
            world_building_hooks=[
                f"The world of {brief.project_name} exists in a delicate balance",
                "Ancient powers stir beneath the surface",
                "A forgotten civilization left behind more than ruins",
            ],
            character_relationships=[
                {"characters": "protagonist_ally", "dynamic": "trust_built_through_trials"},
                {"characters": "protagonist_rival", "dynamic": "respect_through_competition"},
            ],
            branching_opportunities=[
                "Major faction alignment choice at midpoint",
                "Moral dilemma affecting world state",
                "Companion loyalty determined by actions",
            ],
            emotional_beats=[
                f"{brief.emotional_tone.value} opening that establishes the world",
                "Rising tension through discovery",
                "Cathartic resolution with lasting consequences",
            ],
        )

        self._themes[theme.id] = theme
        return theme

    def design_audio_direction(
        self,
        brief_id: str,
    ) -> AudioDirection:
        brief = self._briefs.get(brief_id)
        if not brief:
            raise ValueError(f"Creative brief '{brief_id}' not found")

        soundtrack_by_tone = {
            EmotionalTone.HOPEFUL: "orchestral_adventure",
            EmotionalTone.EPIC: "symphonic_power",
            EmotionalTone.MYSTERIOUS: "ambient_electronic",
            EmotionalTone.DARK: "dark_atmospheric",
            EmotionalTone.MELANCHOLIC: "solo_piano_strings",
            EmotionalTone.TENSE: "minimal_percussion",
        }

        instruments_by_style = {
            VisualStyle.PIXEL_ART: ["chiptune_lead", "square_wave_bass", "8bit_percussion"],
            VisualStyle.STYLIZED: ["orchestral_strings", "piano", "world_percussion"],
            VisualStyle.CEL_SHADED: ["electric_guitar", "synth_pad", "driving_drums"],
            VisualStyle.HAND_DRAWN: ["acoustic_guitar", "cello", "light_percussion"],
        }

        audio = AudioDirection(
            soundtrack_genre=soundtrack_by_tone.get(brief.emotional_tone, "adaptive_score"),
            instrumentation=instruments_by_style.get(brief.visual_style, ["piano", "strings", "ambient_pad"]),
            tempo_range=(90.0, 150.0) if brief.genre in (GenreCategory.ACTION, GenreCategory.SHOOTER) else (70.0, 120.0),
            dynamic_range="wide" if brief.emotional_tone == EmotionalTone.EPIC else "moderate",
            ambient_style="procedural_layered" if brief.target_audience == TargetAudience.CORE else "subtle_drone",
            sfx_design_approach="juicy_exaggerated" if brief.visual_style == VisualStyle.STYLIZED else "grounded",
            leitmotif_themes=[f"{brief.project_name}_main_theme", "exploration_theme", "conflict_theme"],
        )

        self._audio_directions[audio.id] = audio
        return audio

    def map_player_experience(
        self,
        brief_id: str,
    ) -> PlayerExperienceMap:
        brief = self._briefs.get(brief_id)
        if not brief:
            raise ValueError(f"Creative brief '{brief_id}' not found")

        journey_segments = 8
        engagement = []
        emotional_journey = []

        for i in range(journey_segments):
            t = i / (journey_segments - 1)
            engagement.append(round(0.3 + 0.4 * math.sin(t * math.pi) + 0.15 * (1.0 if t > 0.5 else -1.0), 3))

            if i == 0:
                emotion = "curiosity_and_wonder"
            elif i == journey_segments - 1:
                emotion = "catharsis_and_fulfillment"
            elif 0.4 <= t <= 0.6:
                emotion = "rising_tension_and_revelation"
            else:
                emotion = "exploration_and_growth"

            emotional_journey.append({
                "segment": i,
                "progression": round(t, 2),
                "emotion": emotion,
                "intensity": round(0.3 + 0.5 * math.sin(t * math.pi), 2),
            })

        exp_map = PlayerExperienceMap(
            emotional_journey=emotional_journey,
            engagement_curve=engagement,
            key_moments=[
                {"name": "Opening Hook", "timing": "first_5_minutes", "emotion": "intrigue"},
                {"name": "First Major Choice", "timing": "act_one_end", "emotion": "empowerment"},
                {"name": "Midpoint Revelation", "timing": "act_two_mid", "emotion": "shock"},
                {"name": "Climactic Confrontation", "timing": "act_three_finale", "emotion": "triumph"},
            ],
            difficulty_progression="gradual_with_spikes",
            learning_curve_steepness=0.3 if brief.target_audience == TargetAudience.CASUAL else 0.6,
            replayability_factors=[
                "Branching narrative paths with meaningful consequences",
                "Multiple character builds and playstyle expressions",
                "Hidden content rewarding thorough exploration",
            ],
            social_experience="solo",
            accessibility_features=[
                "Customizable difficulty at any point",
                "Full controller remapping",
                "Subtitle options with speaker identification",
                "Color-blind friendly palette modes",
            ],
        )

        self._experience_maps[exp_map.id] = exp_map
        return exp_map

    def get_brief(self, brief_id: str) -> Optional[CreativeBrief]:
        return self._briefs.get(brief_id)

    def get_pillars_for_brief(self, brief_id: str) -> List[GameplayPillar]:
        return [p for p in self._pillars.values() if p.id]

    def get_art_profile_for_brief(self, brief_id: str) -> Optional[ArtDirectionProfile]:
        profiles = list(self._art_profiles.values())
        return profiles[-1] if profiles else None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_briefs_generated": self._total_briefs_generated,
            "total_pillars_defined": self._total_pillars_defined,
            "total_art_profiles": self._total_art_profiles,
            "total_mood_descriptors": len(self._moods),
            "total_narrative_themes": len(self._themes),
            "total_audio_directions": len(self._audio_directions),
            "total_experience_maps": len(self._experience_maps),
            "available_genre_templates": len(_GENRE_PILLAR_TEMPLATES),
            "available_style_palettes": len(_STYLE_PALETTES),
            "available_mood_templates": len(_MOOD_TEMPLATES),
        }


def get_creative_director() -> AgentCreativeDirector:
    return AgentCreativeDirector()