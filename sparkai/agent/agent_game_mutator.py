"""
SparkLabs Agent - Game Mutation Engine

Creates controlled variations of generated games by mutating specific
design parameters. Enables design-space exploration, A/B testing, and
iterative refinement without regenerating from scratch.

The mutator parses the game HTML to identify mutable parameters,
applies targeted mutations (difficulty shifts, theme swaps, mechanic
tweaks, layout changes), and produces a variant game that can be
compared against the original.

Mutation strategies:
  - difficulty_ramp   : scale enemy speed, count, and damage
  - theme_shift       : swap color palette and background
  - pace_adjust       : modify gravity, jump strength, move speed
  - density_change    : alter collectible and enemy counts
  - gravity_flip      : invert gravity for novel mechanics
  - palette_invert    : dark-to-light or light-to-dark inversion
  - size_scale        : scale entity sizes for accessibility
  - speed_boost       : global time-scale multiplier

Architecture:
  GameMutator (singleton)
    |-- ParameterExtractor -> finds mutable values in game HTML
    |-- MutationStrategy   -> defines how each mutation transforms params
    |-- VariantBuilder     -> applies mutations and produces variant HTML
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class MutationStrategy:
    """Definition of a single mutation strategy."""
    strategy_id: str
    name: str
    description: str
    category: str  # difficulty, visual, pace, density, accessibility
    mutations: Dict[str, Any]  # param_name -> new_value or scale_factor


@dataclass
class GameParameters:
    """Extracted mutable parameters from a game's HTML."""
    enemy_speed: float = 1.5
    move_speed: float = 4.0
    gravity: float = 0.5
    jump_strength: float = 11.0
    collectible_count: int = 8
    enemy_count: int = 4
    lives: int = 3
    background: str = "#1a1a2e"
    accent_color: str = "#f97316"
    player_color: str = "#f97316"
    enemy_color: str = "#ef4444"
    collectible_color: str = "#fbbf24"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enemy_speed": self.enemy_speed,
            "move_speed": self.move_speed,
            "gravity": self.gravity,
            "jump_strength": self.jump_strength,
            "collectible_count": self.collectible_count,
            "enemy_count": self.enemy_count,
            "lives": self.lives,
            "background": self.background,
            "accent_color": self.accent_color,
            "player_color": self.player_color,
            "enemy_color": self.enemy_color,
            "collectible_color": self.collectible_color,
        }


@dataclass
class MutationResult:
    """Result of a game mutation operation."""
    success: bool
    session_id: str
    original_html: str = ""
    variant_html: str = ""
    strategy: Optional[MutationStrategy] = None
    original_params: Optional[GameParameters] = None
    variant_params: Optional[GameParameters] = None
    changes: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    error: Optional[str] = None

    def to_dict(self, include_html: bool = False) -> Dict[str, Any]:
        d = {
            "success": self.success,
            "session_id": self.session_id,
            "original_html_length": len(self.original_html),
            "variant_html_length": len(self.variant_html),
            "strategy": {
                "strategy_id": self.strategy.strategy_id,
                "name": self.strategy.name,
                "description": self.strategy.description,
                "category": self.strategy.category,
            } if self.strategy else None,
            "original_params": self.original_params.to_dict() if self.original_params else None,
            "variant_params": self.variant_params.to_dict() if self.variant_params else None,
            "changes": list(self.changes),
            "duration_s": round(self.duration_s, 4),
            "error": self.error,
        }
        if include_html:
            d["original_html"] = self.original_html
            d["variant_html"] = self.variant_html
        return d


# =============================================================================
# Parameter Extractor - Parse mutable values from game HTML
# =============================================================================


class ParameterExtractor:
    """Extracts mutable game parameters from generated HTML."""

    # Regex patterns for finding CONFIG values in the game HTML
    PATTERNS = {
        "enemy_speed": re.compile(r'enemySpeed["\']?\s*[:=]\s*([0-9.]+)', re.I),
        "move_speed": re.compile(r'moveSpeed["\']?\s*[:=]\s*([0-9.]+)', re.I),
        "gravity": re.compile(r'gravity["\']?\s*[:=]\s*([0-9.]+)', re.I),
        "jump_strength": re.compile(r'jumpStrength["\']?\s*[:=]\s*([0-9.]+)', re.I),
        "collectible_count": re.compile(r'collectibleCount["\']?\s*[:=]\s*(\d+)', re.I),
        "enemy_count": re.compile(r'enemyCount["\']?\s*[:=]\s*(\d+)', re.I),
        "lives": re.compile(r'lives["\']?\s*[:=]\s*(\d+)', re.I),
        "background": re.compile(r'backgroundColor["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.I),
        "accent_color": re.compile(r'accentColor["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.I),
        "player_color": re.compile(r'playerColor["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.I),
        "enemy_color": re.compile(r'enemyColor["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.I),
        "collectible_color": re.compile(r'collectibleColor["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.I),
    }

    # Fallback patterns for CONFIG object properties (JSON format: "key": value)
    CONFIG_PATTERNS = {
        "enemy_speed": re.compile(r'"enemySpeed":\s*([0-9.]+)', re.I),
        "move_speed": re.compile(r'"moveSpeed":\s*([0-9.]+)', re.I),
        "gravity": re.compile(r'"gravity":\s*([0-9.]+)', re.I),
        "jump_strength": re.compile(r'"jumpStrength":\s*([0-9.]+)', re.I),
        "collectible_count": re.compile(r'"collectibleCount":\s*(\d+)', re.I),
        "enemy_count": re.compile(r'"enemyCount":\s*(\d+)', re.I),
        "lives": re.compile(r'"lives":\s*(\d+)', re.I),
        "background": re.compile(r'"backgroundColor":\s*"([^"]+)"', re.I),
        "accent_color": re.compile(r'"accentColor":\s*"([^"]+)"', re.I),
        "player_color": re.compile(r'"playerColor":\s*"([^"]+)"', re.I),
        "enemy_color": re.compile(r'"enemyColor":\s*"([^"]+)"', re.I),
        "collectible_color": re.compile(r'"collectibleColor":\s*"([^"]+)"', re.I),
    }

    @classmethod
    def extract(cls, html: str) -> GameParameters:
        """Extract game parameters from HTML by searching for CONFIG values."""
        params = GameParameters()

        for key, pattern in cls.CONFIG_PATTERNS.items():
            match = pattern.search(html)
            if match:
                raw = match.group(1)
                if key in ("enemy_speed", "move_speed", "gravity", "jump_strength"):
                    setattr(params, key, float(raw))
                elif key in ("collectible_count", "enemy_count", "lives"):
                    setattr(params, key, int(raw))
                else:
                    setattr(params, key, raw)

        return params


# =============================================================================
# Mutation Strategy Catalog
# =============================================================================


STRATEGY_CATALOG: List[Dict[str, Any]] = [
    {
        "strategy_id": "difficulty_ramp",
        "name": "Difficulty Ramp",
        "description": "Increase enemy speed by 40%, enemy count by 50%, reduce lives by 1",
        "category": "difficulty",
        "mutations": {
            "enemy_speed": "scale_1.4",
            "enemy_count": "scale_1.5",
            "lives": "delta_-1",
        },
    },
    {
        "strategy_id": "difficulty_ease",
        "name": "Difficulty Ease",
        "description": "Decrease enemy speed by 30%, reduce enemy count by 25%, add 1 life",
        "category": "difficulty",
        "mutations": {
            "enemy_speed": "scale_0.7",
            "enemy_count": "scale_0.75",
            "lives": "delta_+1",
        },
    },
    {
        "strategy_id": "pace_frenetic",
        "name": "Frenetic Pace",
        "description": "Boost move speed by 50%, increase gravity by 20%, stronger jumps",
        "category": "pace",
        "mutations": {
            "move_speed": "scale_1.5",
            "gravity": "scale_1.2",
            "jump_strength": "scale_1.15",
        },
    },
    {
        "strategy_id": "pace_floaty",
        "name": "Floaty Pace",
        "description": "Reduce gravity by 40%, lower move speed, gentle jumps for exploration",
        "category": "pace",
        "mutations": {
            "move_speed": "scale_0.8",
            "gravity": "scale_0.6",
            "jump_strength": "scale_0.85",
        },
    },
    {
        "strategy_id": "density_swarm",
        "name": "Enemy Swarm",
        "description": "Double enemy count, reduce collectibles, test combat focus",
        "category": "density",
        "mutations": {
            "enemy_count": "scale_2.0",
            "collectible_count": "scale_0.5",
        },
    },
    {
        "strategy_id": "density_harvest",
        "name": "Harvest Mode",
        "description": "Double collectibles, halve enemies, test collection focus",
        "category": "density",
        "mutations": {
            "collectible_count": "scale_2.0",
            "enemy_count": "scale_0.5",
        },
    },
    {
        "strategy_id": "theme_midnight",
        "name": "Midnight Theme",
        "description": "Dark background with neon accent colors",
        "category": "visual",
        "mutations": {
            "background": "#050510",
            "accent_color": "#00ffff",
            "player_color": "#00ffff",
            "enemy_color": "#ff00aa",
            "collectible_color": "#ffff00",
        },
    },
    {
        "strategy_id": "theme_forest",
        "name": "Forest Theme",
        "description": "Green background with earthy tones",
        "category": "visual",
        "mutations": {
            "background": "#0a1f0a",
            "accent_color": "#22c55e",
            "player_color": "#fbbf24",
            "enemy_color": "#dc2626",
            "collectible_color": "#f59e0b",
        },
    },
    {
        "strategy_id": "theme_sunset",
        "name": "Sunset Theme",
        "description": "Warm purple-orange palette",
        "category": "visual",
        "mutations": {
            "background": "#1a0a2e",
            "accent_color": "#f97316",
            "player_color": "#fbbf24",
            "enemy_color": "#ec4899",
            "collectible_color": "#f59e0b",
        },
    },
    {
        "strategy_id": "gravity_flip",
        "name": "Gravity Flip",
        "description": "Invert gravity for novel upside-down mechanics",
        "category": "mechanic",
        "mutations": {
            "gravity": "negate",
        },
    },
]


# =============================================================================
# Variant Builder - Apply mutations to produce variant HTML
# =============================================================================


class VariantBuilder:
    """Applies mutation strategies to game HTML, producing variants."""

    @staticmethod
    def apply_mutation(value: Any, mutation: str) -> Any:
        """Apply a single mutation directive to a value.

        Mutation formats:
          scale_X.Y  -> multiply numeric by factor
          delta_+N   -> add N to numeric
          delta_-N   -> subtract N from numeric
          negate     -> negate numeric
          literal    -> replace with literal value
        """
        if isinstance(value, (int, float)):
            if mutation == "negate":
                return -value
            if mutation.startswith("scale_"):
                factor = float(mutation[6:])
                result = value * factor
                return int(result) if isinstance(value, int) else result
            if mutation.startswith("delta_"):
                delta_str = mutation[6:]
                delta = float(delta_str)
                result = value + delta
                return int(result) if isinstance(value, int) else result
            # Direct literal replacement
            try:
                return float(mutation) if isinstance(value, float) else int(mutation)
            except ValueError:
                return value
        else:
            # String replacement (color, background)
            return mutation

    @staticmethod
    def build_variant(
        html: str,
        original_params: GameParameters,
        strategy: MutationStrategy,
    ) -> Tuple[str, GameParameters, List[str]]:
        """Apply a mutation strategy to game HTML.

        Returns (variant_html, variant_params, change_descriptions).
        """
        variant_params = GameParameters(
            enemy_speed=original_params.enemy_speed,
            move_speed=original_params.move_speed,
            gravity=original_params.gravity,
            jump_strength=original_params.jump_strength,
            collectible_count=original_params.collectible_count,
            enemy_count=original_params.enemy_count,
            lives=original_params.lives,
            background=original_params.background,
            accent_color=original_params.accent_color,
            player_color=original_params.player_color,
            enemy_color=original_params.enemy_color,
            collectible_color=original_params.collectible_color,
        )

        changes: List[str] = []
        variant_html = html

        for param_name, mutation in strategy.mutations.items():
            old_value = getattr(variant_params, param_name)
            new_value = VariantBuilder.apply_mutation(old_value, mutation)
            setattr(variant_params, param_name, new_value)

            changes.append(
                f"{param_name}: {old_value} -> {new_value}"
            )

            # Apply the change to the HTML
            variant_html = VariantBuilder._replace_in_html(
                variant_html, param_name, old_value, new_value
            )

        return variant_html, variant_params, changes

    @staticmethod
    def _replace_in_html(
        html: str, param_name: str, old_value: Any, new_value: Any,
    ) -> str:
        """Replace a parameter value in the game HTML.

        Handles both CONFIG object property format (key: value)
        and assignment format (key = value).
        """
        # Map param_name to the JS property name
        js_key_map = {
            "enemy_speed": "enemySpeed",
            "move_speed": "moveSpeed",
            "gravity": "gravity",
            "jump_strength": "jumpStrength",
            "collectible_count": "collectibleCount",
            "enemy_count": "enemyCount",
            "lives": "lives",
            "background": "backgroundColor",
            "accent_color": "accentColor",
            "player_color": "playerColor",
            "enemy_color": "enemyColor",
            "collectible_color": "collectibleColor",
        }

        js_key = js_key_map.get(param_name, param_name)

        # For numeric values, replace in CONFIG JSON object
        if isinstance(old_value, (int, float)):
            old_str = str(old_value)
            new_str = str(new_value)

            # Pattern: "key": old_value (JSON format in CONFIG)
            pattern1 = re.compile(
                rf'("{js_key}":\s*){re.escape(old_str)}',
                re.I,
            )
            html = pattern1.sub(rf'\g<1>{new_str}', html)

            # Pattern: key = old_value (assignment, for runtime overrides)
            pattern2 = re.compile(
                rf'({js_key}\s*=\s*){re.escape(old_str)}',
                re.I,
            )
            html = pattern2.sub(rf'\g<1>{new_str}', html)

        # For string values (colors), replace quoted strings
        elif isinstance(old_value, str):
            old_str = old_value
            new_str = str(new_value)

            # Pattern: "key": "old_value" (JSON format in CONFIG)
            pattern1 = re.compile(
                rf'("{js_key}":\s*"){re.escape(old_str)}(")',
                re.I,
            )
            html = pattern1.sub(rf'\g<1>{new_str}\g<2>', html)

        return html


# =============================================================================
# Game Mutator (Singleton)
# =============================================================================


class GameMutator:
    """
    Top-level mutator that creates game variants by applying mutation
    strategies to generated game HTML.
    """

    _instance: Optional["GameMutator"] = None
    _lock = threading.RLock()

    def __init__(self):
        self._extractor = ParameterExtractor
        self._builder = VariantBuilder()
        self._strategies: Dict[str, MutationStrategy] = {}
        self._history: List[Dict[str, Any]] = []
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "GameMutator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Load the strategy catalog."""
        for entry in STRATEGY_CATALOG:
            strategy = MutationStrategy(
                strategy_id=entry["strategy_id"],
                name=entry["name"],
                description=entry["description"],
                category=entry["category"],
                mutations=entry["mutations"],
            )
            self._strategies[strategy.strategy_id] = strategy
        self._initialized = True
        logger.info("GameMutator initialized with %d strategies", len(self._strategies))

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "strategy_count": len(self._strategies),
            "history_count": len(self._history),
        }

    def get_strategies(self) -> List[Dict[str, Any]]:
        """List all available mutation strategies."""
        return [
            {
                "strategy_id": s.strategy_id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
            }
            for s in self._strategies.values()
        ]

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def mutate(
        self,
        html: str,
        strategy_id: str,
    ) -> MutationResult:
        """Apply a mutation strategy to game HTML.

        Args:
            html: The original game HTML
            strategy_id: Which mutation strategy to apply

        Returns:
            MutationResult with the variant HTML and metadata
        """
        start = time.time()
        session_id = f"mut_{uuid.uuid4().hex[:12]}"

        if not self._initialized:
            self.initialize()

        if not html or not html.strip():
            return MutationResult(
                success=False, session_id=session_id,
                error="HTML content is required",
                duration_s=0.0,
            )

        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return MutationResult(
                success=False, session_id=session_id,
                error=f"Unknown strategy: {strategy_id}",
                duration_s=0.0,
            )

        try:
            # Extract original parameters
            original_params = self._extractor.extract(html)

            # Build variant
            variant_html, variant_params, changes = self._builder.build_variant(
                html, original_params, strategy,
            )

            duration = time.time() - start
            result = MutationResult(
                success=True,
                session_id=session_id,
                original_html=html,
                variant_html=variant_html,
                strategy=strategy,
                original_params=original_params,
                variant_params=variant_params,
                changes=changes,
                duration_s=duration,
            )

            self._history.append(result.to_dict(include_html=False))
            if len(self._history) > 30:
                self._history = self._history[-30:]

            return result

        except Exception as e:
            logger.exception("Game mutation failed")
            return MutationResult(
                success=False, session_id=session_id,
                error=str(e),
                duration_s=time.time() - start,
            )

    def mutate_batch(
        self,
        html: str,
        strategy_ids: Optional[List[str]] = None,
    ) -> List[MutationResult]:
        """Apply multiple mutation strategies to the same game HTML.

        Args:
            html: The original game HTML
            strategy_ids: List of strategies to apply (None = all)

        Returns:
            List of MutationResults, one per strategy
        """
        if not self._initialized:
            self.initialize()

        if strategy_ids is None:
            strategy_ids = list(self._strategies.keys())

        results: List[MutationResult] = []
        for sid in strategy_ids:
            result = self.mutate(html, sid)
            results.append(result)

        return results


# =============================================================================
# Module-level accessor
# =============================================================================


def get_game_mutator() -> GameMutator:
    """Return the singleton GameMutator instance."""
    return GameMutator.get_instance()
