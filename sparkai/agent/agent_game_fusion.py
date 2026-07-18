"""
SparkLabs Agent - Game Fusion

The penultimate agent in the AI-native pipeline. After the Tournament
selects a champion, the Fusion agent analyzes ALL competing variants,
identifies each one's strongest dimensions (via the Game Critic), and
fuses the best parameters from each into a single superior game.

Architecture:
  GameFusion (Singleton)
    |-- GameCriticAgent  -> per-dimension quality scores (10 dimensions)
    |-- Config Extractor -> parses CONFIG JSON from game HTML
    |-- Fusion Engine    -> merges best parameters by dimension dominance

Fusion strategy:
  1. Evaluate each variant through the Critic to get dimension scores
  2. Extract CONFIG parameters from each variant's HTML
  3. For each parameter domain, select the variant that dominates the
     relevant dimension (e.g. difficulty params from the variant with
     the highest "difficulty" score)
  4. Use the highest composite variant as the base HTML template
  5. Inject the fused CONFIG into the base template
  6. Produce a fusion manifest tracing each parameter to its source

Usage:
    fusion = GameFusion.get_instance()
    fusion.initialize()
    result = fusion.fuse(variants, game_title="My Game")
    # result.html contains the fused game
    # result.manifest shows which parameters came from which variant
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Dimension → Parameter Domain Mapping
# =============================================================================

# Each Critic dimension maps to a set of CONFIG parameter keywords.
# When a variant dominates a dimension, its matching parameters are
# preferred during fusion.
DIMENSION_PARAM_MAP: Dict[str, List[str]] = {
    "fun": ["score", "combo", "multiplier", "bonus", "reward", "power"],
    "pacing": ["level_count", "levels", "stage", "wave", "round"],
    "difficulty": ["difficulty", "enemySpeed", "enemyHealth", "spawnRate",
                   "damage", "aiLevel", "challenge"],
    "narrative": ["story", "dialogue", "quest", "character", "plot"],
    "visuals": ["width", "height", "color", "theme", "palette", "bgColor",
                "particleCount", "screenShake"],
    "audio": ["volume", "bgm", "sfx", "music", "sound"],
    "accessibility": ["fontSize", "contrast", "colorblind", "subtitle"],
    "replayability": ["seed", "random", "procedural", "endless", "loop"],
    "innovation": ["gravity", "physics", "mechanic", "special", "unique"],
    "polish": ["fps", "vsync", "antialias", "quality", "resolution"],
}

# Parameters that affect the overall game structure and should be taken
# from the best overall variant if no dimension dominates
STRUCTURAL_PARAMS = ["level_count", "difficulty_score", "genre"]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class VariantAnalysis:
    """Analysis of a single variant during fusion."""

    entry_id: str
    label: str
    html: str
    source: str
    critic_score: float = 0.0
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    html_length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "label": self.label,
            "source": self.source,
            "critic_score": round(self.critic_score, 2),
            "dimension_scores": {k: round(v, 2) for k, v in self.dimension_scores.items()},
            "config": dict(self.config),
            "html_length": self.html_length,
        }


@dataclass
class FusionManifest:
    """Manifest tracing each fused parameter to its source variant."""

    param_name: str
    value: Any
    source_label: str
    source_dimension: str
    source_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param": self.param_name,
            "value": self.value,
            "source": self.source_label,
            "dimension": self.source_dimension,
            "score": round(self.source_score, 2),
        }


@dataclass
class FusionResult:
    """Complete result of a fusion operation."""

    fusion_id: str
    success: bool
    game_title: str
    variant_count: int
    html: str
    fused_config: Dict[str, Any]
    manifest: List[FusionManifest]
    variants: List[VariantAnalysis]
    dimension_winners: Dict[str, str]  # dimension -> variant label
    base_variant: str  # label of the base HTML template
    improvement_estimate: float  # estimated improvement over best single variant
    duration_s: float
    error: Optional[str] = None

    def to_dict(self, include_html: bool = True) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "fusion_id": self.fusion_id,
            "success": self.success,
            "game_title": self.game_title,
            "variant_count": self.variant_count,
            "fused_config": dict(self.fused_config),
            "manifest": [m.to_dict() for m in self.manifest],
            "variants": [v.to_dict() for v in self.variants],
            "dimension_winners": dict(self.dimension_winners),
            "base_variant": self.base_variant,
            "improvement_estimate": round(self.improvement_estimate, 2),
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
        }
        if include_html:
            result["html"] = self.html
        return result


# =============================================================================
# Game Fusion Agent
# =============================================================================


class GameFusion:
    """
    Fuses the strengths of multiple game variants into a single superior game.

    The agent evaluates each variant through the Game Critic, extracts CONFIG
    parameters from each, and builds a fused game that takes the best
    parameters from each variant based on dimension dominance.

    Implements a thread-safe singleton pattern.
    """

    _instance: Optional["GameFusion"] = None
    _instance_lock = threading.RLock()

    # Regex patterns for CONFIG extraction
    _CONFIG_PATTERNS = [
        # const CONFIG = {...};
        re.compile(r"const\s+CONFIG\s*=\s*(\{[^}]+\})", re.DOTALL),
        # var CONFIG = {...};
        re.compile(r"var\s+CONFIG\s*=\s*(\{[^}]+\})", re.DOTALL),
        # let CONFIG = {...};
        re.compile(r"let\s+CONFIG\s*=\s*(\{[^}]+\})", re.DOTALL),
        # window.CONFIG = {...};
        re.compile(r"window\.CONFIG\s*=\s*(\{[^}]+\})", re.DOTALL),
    ]

    def __init__(self) -> None:
        if GameFusion._instance is not None:
            raise RuntimeError("Use GameFusion.get_instance()")
        self._initialized: bool = False
        self._critic: Any = None
        self._history: deque = deque(maxlen=30)
        self._total_fusions: int = 0
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GameFusion":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the fusion agent by acquiring the Critic singleton."""
        with self._lock:
            if self._initialized:
                return
            try:
                from sparkai.agent.agent_game_critic import GameCriticAgent
                self._critic = GameCriticAgent.get_instance()
            except Exception as exc:
                logger.warning("GameCriticAgent acquisition failed: %s", exc)
                self._critic = None
            self._initialized = True
            logger.info("GameFusion initialized")

    # -- Public API --------------------------------------------------------

    def fuse(
        self,
        variants: List[Dict[str, Any]],
        game_title: str = "Fused Game",
        genre: str = "",
    ) -> FusionResult:
        """
        Fuse multiple game variants into a single superior game.

        Args:
            variants: List of dicts with keys "html" (required), "label"
                      (optional), "source" (optional)
            game_title: Title for the fused game
            genre: Optional genre hint for evaluation

        Returns:
            FusionResult with the fused HTML and manifest
        """
        if not self._initialized:
            self.initialize()

        fusion_id = f"fusion_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        try:
            # Phase 1: Analyze all variants
            analyses = self._analyze_variants(variants, game_title, genre)
            if len(analyses) < 2:
                return FusionResult(
                    fusion_id=fusion_id,
                    success=False,
                    game_title=game_title,
                    variant_count=len(analyses),
                    html="",
                    fused_config={},
                    manifest=[],
                    variants=analyses,
                    dimension_winners={},
                    base_variant="",
                    improvement_estimate=0.0,
                    duration_s=time.time() - start_time,
                    error="At least 2 variants are required for fusion",
                )

            # Phase 2: Determine dimension winners
            dimension_winners = self._find_dimension_winners(analyses)

            # Phase 3: Select base variant (highest overall critic score)
            base = max(analyses, key=lambda a: a.critic_score)

            # Phase 4: Build fused CONFIG
            fused_config, manifest = self._build_fused_config(
                analyses, base, dimension_winners
            )

            # Phase 5: Inject fused CONFIG into base HTML
            fused_html = self._inject_config(base.html, fused_config)

            # Phase 6: Estimate improvement
            best_single = max(a.critic_score for a in analyses)
            avg_dim_winner_score = self._estimate_fused_score(
                analyses, dimension_winners
            )
            improvement = max(0.0, avg_dim_winner_score - best_single)

            duration = time.time() - start_time
            result = FusionResult(
                fusion_id=fusion_id,
                success=True,
                game_title=game_title,
                variant_count=len(analyses),
                html=fused_html,
                fused_config=fused_config,
                manifest=manifest,
                variants=analyses,
                dimension_winners=dimension_winners,
                base_variant=base.label,
                improvement_estimate=improvement,
                duration_s=duration,
            )

            with self._lock:
                self._history.append(result)
                self._total_fusions += 1

            logger.info(
                "Fusion %s complete: base=%s, %d params fused from %d variants, "
                "improvement estimate +%.2f",
                fusion_id, base.label, len(manifest), len(analyses), improvement,
            )
            return result

        except Exception as exc:
            logger.exception("Fusion %s failed: %s", fusion_id, exc)
            return FusionResult(
                fusion_id=fusion_id,
                success=False,
                game_title=game_title,
                variant_count=len(variants),
                html="",
                fused_config={},
                manifest=[],
                variants=[],
                dimension_winners={},
                base_variant="",
                improvement_estimate=0.0,
                duration_s=time.time() - start_time,
                error=str(exc),
            )

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the fusion agent."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_fusions": self._total_fusions,
                "dimensions": list(DIMENSION_PARAM_MAP.keys()),
                "min_variants": 2,
                "max_variants": 16,
            }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent fusion results."""
        with self._lock:
            return [r.to_dict(include_html=False) for r in list(self._history)[-limit:]]

    # -- Internal: Analysis ------------------------------------------------

    def _analyze_variants(
        self,
        variants: List[Dict[str, Any]],
        game_title: str,
        genre: str,
    ) -> List[VariantAnalysis]:
        """Analyze each variant: evaluate through Critic and extract CONFIG."""
        analyses: List[VariantAnalysis] = []

        for i, v in enumerate(variants):
            html = v.get("html", "")
            if not html or not html.strip():
                continue

            label = v.get("label", f"Variant {i + 1}")
            source = v.get("source", "manual")
            entry_id = f"variant_{uuid.uuid4().hex[:8]}"

            # Extract CONFIG from HTML
            config = self._extract_config(html)

            # Evaluate through Critic
            critic_score = 5.0
            dimension_scores: Dict[str, float] = {}
            if self._critic is not None:
                try:
                    result = self._critic.critique_game(
                        html=html,
                        game_title=f"{game_title} - {label}",
                        genre=genre,
                    )
                    report = result.get("report")
                    if report:
                        critic_score = report.get("overall_score", 5.0)
                        dimension_scores = report.get("dimension_scores", {})
                except Exception as exc:
                    logger.warning("Critic evaluation failed for %s: %s", label, exc)

            analyses.append(VariantAnalysis(
                entry_id=entry_id,
                label=label,
                html=html,
                source=source,
                critic_score=critic_score,
                dimension_scores=dimension_scores,
                config=config,
                html_length=len(html),
            ))

        return analyses

    # -- Internal: Dimension Winners ---------------------------------------

    def _find_dimension_winners(
        self, analyses: List[VariantAnalysis]
    ) -> Dict[str, str]:
        """Find which variant wins each dimension."""
        winners: Dict[str, str] = {}
        all_dims = set()
        for a in analyses:
            all_dims.update(a.dimension_scores.keys())

        for dim in all_dims:
            best_score = -1.0
            best_label = ""
            for a in analyses:
                score = a.dimension_scores.get(dim, 0.0)
                if score > best_score:
                    best_score = score
                    best_label = a.label
            if best_label:
                winners[dim] = best_label
        return winners

    # -- Internal: Fused CONFIG Building ----------------------------------

    def _build_fused_config(
        self,
        analyses: List[VariantAnalysis],
        base: VariantAnalysis,
        dimension_winners: Dict[str, str],
    ) -> Tuple[Dict[str, Any], List[FusionManifest]]:
        """
        Build a fused CONFIG by taking the best parameters from each variant
        based on dimension dominance.
        """
        # Start with the base variant's config
        fused: Dict[str, Any] = dict(base.config)
        manifest: List[FusionManifest] = []

        # Track which params have been assigned
        assigned_params: set = set()

        # For each dimension, take the winning variant's matching params
        for dim, winner_label in dimension_winners.items():
            winner = next(
                (a for a in analyses if a.label == winner_label), None
            )
            if winner is None:
                continue

            param_keywords = DIMENSION_PARAM_MAP.get(dim, [])
            winner_score = winner.dimension_scores.get(dim, 0.0)

            for param_name, param_value in winner.config.items():
                # Check if this param matches the dimension's keywords
                param_lower = param_name.lower()
                matches = any(kw.lower() in param_lower for kw in param_keywords)
                if not matches:
                    continue
                # Only override if the winner's value is different and better
                if param_name in assigned_params:
                    continue

                fused[param_name] = param_value
                assigned_params.add(param_name)
                manifest.append(FusionManifest(
                    param_name=param_name,
                    value=param_value,
                    source_label=winner_label,
                    source_dimension=dim,
                    source_score=winner_score,
                ))

        # Fill in any remaining params from the base variant
        for param_name, param_value in base.config.items():
            if param_name not in assigned_params:
                fused[param_name] = param_value
                manifest.append(FusionManifest(
                    param_name=param_name,
                    value=param_value,
                    source_label=base.label,
                    source_dimension="overall",
                    source_score=base.critic_score,
                ))

        return fused, manifest

    # -- Internal: CONFIG Extraction & Injection ---------------------------

    def _extract_config(self, html: str) -> Dict[str, Any]:
        """Extract CONFIG JSON from game HTML."""
        for pattern in self._CONFIG_PATTERNS:
            match = pattern.search(html)
            if match:
                try:
                    # Try to parse the JSON object
                    config_str = match.group(1)
                    # Clean up any trailing semicolons or whitespace
                    config_str = config_str.strip().rstrip(";")
                    return json.loads(config_str)
                except (json.JSONDecodeError, IndexError) as exc:
                    logger.debug("CONFIG parse failed with pattern: %s", exc)
                    continue

        # Fallback: try to find any JSON-like object in a script tag
        json_match = re.search(r'\{"[^}]*"difficulty[^}]*\}', html)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}

    def _inject_config(self, html: str, fused_config: Dict[str, Any]) -> str:
        """Inject the fused CONFIG into the HTML, replacing any existing CONFIG."""
        config_json = json.dumps(fused_config, indent=2)
        config_block = f"const CONFIG = {config_json};"

        # Try to replace existing CONFIG
        for pattern in self._CONFIG_PATTERNS:
            if pattern.search(html):
                return pattern.sub(
                    lambda m: config_block.replace(";", ""),
                    html,
                    count=1,
                )

        # No existing CONFIG found, inject before </body>
        injection = f'<script>\n    {config_block}\n</script>\n</body>'
        return html.replace("</body>", injection, 1)

    # -- Internal: Improvement Estimation ---------------------------------

    def _estimate_fused_score(
        self,
        analyses: List[VariantAnalysis],
        dimension_winners: Dict[str, str],
    ) -> float:
        """
        Estimate the fused game's score by averaging the winning scores
        across all dimensions.
        """
        if not dimension_winners:
            return 0.0

        winning_scores: List[float] = []
        for dim, winner_label in dimension_winners.items():
            winner = next(
                (a for a in analyses if a.label == winner_label), None
            )
            if winner:
                winning_scores.append(winner.dimension_scores.get(dim, 0.0))

        if not winning_scores:
            return 0.0

        return sum(winning_scores) / len(winning_scores)


# =============================================================================
# Module-level accessor
# =============================================================================


def get_game_fusion() -> GameFusion:
    """Get the singleton GameFusion instance."""
    return GameFusion.get_instance()
