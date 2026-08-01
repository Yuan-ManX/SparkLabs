"""
SparkLabs Engine - Thematic Resonance Strata

The EngineThematicResonanceStrata treats a story's themes as a layered
resonance field rather than a flat list. Themes do not all live at the
same depth. A surface stratum holds literal, stated themes the player can
point at in dialogue or text. A mid stratum holds recurring motifs that
gesture toward deeper meaning without naming it. A deep stratum holds
archetypal patterns the player feels more than reads. When a theme is
present in all three strata at once, the strata reinforce one another and
the theme is amplified and propagated outward. When a theme only lives at
the surface, with nothing underneath, it slowly fades.

The output is a resonance map: which themes are gathering depth, which
are staying shallow, and how strongly each one vibrates across layers.

Architecture:
  STRATIFY    ->  RESONATE   ->  AMPLIFY    ->  PROPAGATE  ->  INTEGRATE
  (each theme    (cross-       (high-reso-    (amplified     (fold the
   is placed      stratum       nance themes   themes bleed   propagated
   into its       resonance     gain           into adjacent  state back
   surface/mid/   is computed   amplitude;     narrative      into the
   deep presence  for each      isolated       regions,       stratum map;
   values)        theme)        themes decay)  seeding mid-   emit a
                                                level motifs)  resonance
                                                               report)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ResonancePhase(Enum):
    """Phases of the thematic resonance strata cycle."""
    STRATIFY = "stratify"        # assign each theme to its stratum presence
    RESONATE = "resonate"        # compute cross-stratum resonance
    AMPLIFY = "amplify"          # resonant themes gain amplitude, isolated fade
    PROPAGATE = "propagate"      # amplified themes bleed into adjacent regions
    INTEGRATE = "integrate"      # fold propagated state back into the stratum map


class ThemeStratum(Enum):
    """The stratum a theme's presence lives in."""
    SURFACE = "surface"          # literal, stated themes
    MID = "mid"                  # recurring motifs that gesture at deeper meaning
    DEEP = "deep"                # archetypal patterns the player feels more than reads


class ResonanceMode(Enum):
    """How a theme's stratum presences relate to one another."""
    UNISON = "unison"            # all strata strong
    PARTIAL = "partial"          # two strata strong
    ISOLATED = "isolated"        # one stratum only
    DISSONANT = "dissonant"      # strata conflict


class AmplificationDirection(Enum):
    """Direction a theme's amplitude is moving across cycles."""
    RISING = "rising"            # amplitude climbing
    STEADY = "steady"            # amplitude holding
    FADING = "fading"            # amplitude dropping
    DORMANT = "dormant"          # amplitude near zero


class StratumState(Enum):
    """State of the stratum field as a whole."""
    STRATIFYING = "stratifying"  # placing themes into strata
    RESONATING = "resonating"    # measuring cross-stratum resonance
    AMPLIFYING = "amplifying"    # boosting or decaying amplitudes
    PROPAGATING = "propagating"  # bleeding into adjacent regions
    INTEGRATED = "integrated"    # state folded back into the map
    SATURATED = "saturated"      # too many themes near full amplitude


class FieldVitality(Enum):
    """The overall vitality of the resonance field."""
    DORMANT = "dormant"          # few themes, little resonance
    HUMMING = "humming"          # themes present, resonance beginning
    RESONANT = "resonant"        # healthy cross-stratum resonance
    CACOPHONOUS = "cacophonous"  # too many dissonant or saturated themes
    COLLAPSED = "collapsed"      # resonance has failed across the board


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ThemePresence:
    """A theme's presence in each stratum."""
    theme_id: str
    surface: float = 0.0               # 0.0-1.0, literal stated presence
    mid: float = 0.0                   # 0.0-1.0, recurring motif presence
    deep: float = 0.0                  # 0.0-1.0, archetypal presence
    note: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResonanceReading:
    """A reading of how strongly a theme resonates across strata."""
    theme_id: str
    mode: ResonanceMode = ResonanceMode.ISOLATED
    cross_stratum_score: float = 0.0   # 0.0-1.0, how strongly it vibrates across layers
    dominant_stratum: ThemeStratum = ThemeStratum.SURFACE
    note: str = ""


@dataclass
class StrataCycleResult:
    """Summary of a single strata cycle."""
    cycle_count: int
    phase: ResonancePhase = ResonancePhase.INTEGRATE
    phase_outputs: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Engine
# =============================================================================

class EngineThematicResonanceStrata:
    """
    Thread-safe singleton orchestrating the thematic resonance strata field.

    Usage:
        engine = EngineThematicResonanceStrata.get_instance()
        engine.register_theme("loss")
        engine.set_theme_presence("loss", surface=0.7, mid=0.5, deep=0.3)
        engine.cycle()
        reading = engine.get_resonance("loss")
    """

    _instance: Optional["EngineThematicResonanceStrata"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _MAX_THEMES = 48
    _MAX_REGIONS = 32
    _MAX_PROPAGATION_HOPS = 4
    _MAX_EVENTS = 200
    _AMPLIFY_GAIN = 0.18               # amplitude gained per cycle for unison themes
    _AMPLIFY_DECAY = 0.10              # amplitude lost per cycle for isolated themes
    _PROPAGATION_DECAY = 0.6           # amplitude lost per propagation hop
    _RESONANCE_UNISON_THRESHOLD = 0.6  # min stratum value counted as "strong"
    _RESONANCE_PARTIAL_PAIR_MIN = 0.5  # min pair average for partial mode
    _DISSONANCE_SPREAD = 0.55          # gap between high and low stratum that counts as conflict
    _SATURATION_AMPLITUDE = 0.9        # amplitude above which a theme is saturated
    _VITALITY_CACOPHONY_DISSONANT = 4  # dissonant themes before cacophony

    def __init__(self) -> None:
        self._themes: Dict[str, dict] = {}
        self._resonance: Dict[str, ResonanceReading] = {}
        self._phase: ResonancePhase = ResonancePhase.STRATIFY
        self._state: StratumState = StratumState.STRATIFYING
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        # Narrative regions propagation can bleed into.
        self._regions: Dict[str, float] = {}
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineThematicResonanceStrata":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "cycles_completed": 0,
            "themes_stratified": 0,
            "unison_events": 0,
            "partial_resonance_events": 0,
            "isolated_themes_faded": 0,
            "dissonant_events": 0,
            "themes_propagated": 0,
            "last_cycle_at": 0.0,
            "uptime_started_at": time.time(),
            "vitality": FieldVitality.DORMANT.value,
            "avg_cross_stratum_score": 0.0,
            "themes_registered": 0,
            "regions_registered": 0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key in self._stats and isinstance(self._stats[key], (int, float)):
                self._stats[key] += value
            else:
                self._stats[key] = value

    def _derive_vitality(self) -> FieldVitality:
        themes_count = len(self._themes)
        if themes_count == 0:
            return FieldVitality.DORMANT
        dissonant = sum(
            1 for r in self._resonance.values()
            if r.mode == ResonanceMode.DISSONANT
        )
        saturated = sum(
            1 for t in self._themes.values()
            if t.get("amplitude", 0.0) >= self._SATURATION_AMPLITUDE
        )
        avg_score = self._stats.get("avg_cross_stratum_score", 0.0)
        if dissonant >= self._VITALITY_CACOPHONY_DISSONANT and saturated >= 3:
            return FieldVitality.CACOPHONOUS
        if themes_count > 0 and avg_score < 0.1:
            return FieldVitality.COLLAPSED
        if avg_score >= 0.55:
            return FieldVitality.RESONANT
        if avg_score >= 0.25 or themes_count >= 2:
            return FieldVitality.HUMMING
        return FieldVitality.DORMANT

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Theme Management
    # -------------------------------------------------------------------------

    def register_theme(self, theme_id: str, note: str = "") -> Dict[str, Any]:
        """Register a new theme in the resonance field."""
        with self._global_lock:
            if theme_id in self._themes:
                return {"error": f"Theme already registered: {theme_id}"}
            if len(self._themes) >= self._MAX_THEMES:
                return {"error": f"Theme cap reached ({self._MAX_THEMES})"}
            self._themes[theme_id] = {
                "theme_id": theme_id,
                "surface": 0.0,
                "mid": 0.0,
                "deep": 0.0,
                "amplitude": 0.0,
                "direction": AmplificationDirection.DORMANT.value,
                "note": note,
                "created_at": time.time(),
                "regions": {},
            }
            self._resonance[theme_id] = ResonanceReading(theme_id=theme_id)
            self._update_stats(themes_registered=1)
            self._record_event("theme_registered", {"theme_id": theme_id, "note": note})
            return {
                "theme_id": theme_id,
                "surface": 0.0,
                "mid": 0.0,
                "deep": 0.0,
                "amplitude": 0.0,
            }

    def set_theme_presence(self, theme_id: str, surface: float = 0.0,
                           mid: float = 0.0, deep: float = 0.0,
                           note: str = "") -> Dict[str, Any]:
        """Set a theme's presence in each stratum."""
        with self._global_lock:
            theme = self._themes.get(theme_id)
            if theme is None:
                return {"error": f"Theme not found: {theme_id}"}
            theme["surface"] = max(0.0, min(1.0, surface))
            theme["mid"] = max(0.0, min(1.0, mid))
            theme["deep"] = max(0.0, min(1.0, deep))
            if note:
                theme["note"] = note
            self._record_event("theme_presence_set", {
                "theme_id": theme_id,
                "surface": theme["surface"],
                "mid": theme["mid"],
                "deep": theme["deep"],
            })
            return {
                "theme_id": theme_id,
                "surface": theme["surface"],
                "mid": theme["mid"],
                "deep": theme["deep"],
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single resonance strata cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ResonancePhase.STRATIFY
            self._state = StratumState.STRATIFYING
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_stratify()})
            self._phase = ResonancePhase.RESONATE
            self._state = StratumState.RESONATING
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_resonate()})
            self._phase = ResonancePhase.AMPLIFY
            self._state = StratumState.AMPLIFYING
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_amplify()})
            self._phase = ResonancePhase.PROPAGATE
            self._state = StratumState.PROPAGATING
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_propagate()})
            self._phase = ResonancePhase.INTEGRATE
            self._state = StratumState.INTEGRATED
            phase_outputs.append({"phase": self._phase.value,
                                  "result": self._phase_integrate()})
            self._cycle_count += 1
            self._update_stats(
                cycles_completed=1,
                last_cycle_at=time.time(),
            )
            # Refresh derived stats.
            scores = [r.cross_stratum_score for r in self._resonance.values()]
            self._stats["avg_cross_stratum_score"] = (
                sum(scores) / len(scores) if scores else 0.0
            )
            self._stats["themes_registered"] = len(self._themes)
            self._stats["regions_registered"] = len(self._regions)
            self._stats["vitality"] = self._derive_vitality().value
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
                "elapsed_ms": (time.time() - t0) * 1000.0,
            }

    def _phase_stratify(self) -> Dict[str, Any]:
        """Stratify phase: confirm each theme's stratum presence values."""
        stratified = 0
        for theme_id, theme in self._themes.items():
            # Clamp values into the 0-1 range as a defensive measure.
            theme["surface"] = max(0.0, min(1.0, theme.get("surface", 0.0)))
            theme["mid"] = max(0.0, min(1.0, theme.get("mid", 0.0)))
            theme["deep"] = max(0.0, min(1.0, theme.get("deep", 0.0)))
            stratified += 1
        self._update_stats(themes_stratified=stratified)
        self._record_event("phase_stratify", {"stratified": stratified})
        return {"stratified": stratified}

    def _phase_resonate(self) -> Dict[str, Any]:
        """Resonate phase: compute cross-stratum resonance for each theme."""
        unison = 0
        partial = 0
        isolated = 0
        dissonant = 0
        scores: List[float] = []
        for theme_id, theme in self._themes.items():
            s = theme.get("surface", 0.0)
            m = theme.get("mid", 0.0)
            d = theme.get("deep", 0.0)
            mode, score, dominant = self._classify_resonance(s, m, d)
            reading = self._resonance.get(theme_id)
            if reading is None:
                reading = ResonanceReading(theme_id=theme_id)
                self._resonance[theme_id] = reading
            reading.mode = mode
            reading.cross_stratum_score = score
            reading.dominant_stratum = dominant
            reading.note = self._resonance_note(mode, dominant)
            scores.append(score)
            if mode == ResonanceMode.UNISON:
                unison += 1
            elif mode == ResonanceMode.PARTIAL:
                partial += 1
            elif mode == ResonanceMode.ISOLATED:
                isolated += 1
            elif mode == ResonanceMode.DISSONANT:
                dissonant += 1
        self._update_stats(
            unison_events=unison,
            partial_resonance_events=partial,
            dissonant_events=dissonant,
        )
        avg_score = sum(scores) / len(scores) if scores else 0.0
        self._record_event("phase_resonate", {
            "unison": unison,
            "partial": partial,
            "isolated": isolated,
            "dissonant": dissonant,
            "avg_score": avg_score,
        })
        return {
            "unison": unison,
            "partial": partial,
            "isolated": isolated,
            "dissonant": dissonant,
            "avg_score": avg_score,
        }

    def _phase_amplify(self) -> Dict[str, Any]:
        """Amplify phase: resonant themes gain amplitude, isolated themes decay."""
        amplified = 0
        faded = 0
        for theme_id, theme in self._themes.items():
            reading = self._resonance.get(theme_id)
            if reading is None:
                continue
            previous = theme.get("amplitude", 0.0)
            if reading.mode == ResonanceMode.UNISON:
                new_amp = min(1.0, previous + self._AMPLIFY_GAIN)
                amplified += 1
            elif reading.mode == ResonanceMode.PARTIAL:
                new_amp = min(1.0, previous + self._AMPLIFY_GAIN * 0.5)
                amplified += 1
            elif reading.mode == ResonanceMode.DISSONANT:
                # Dissonant themes drift downward, but not as fast as isolated ones.
                new_amp = max(0.0, previous - self._AMPLIFY_DECAY * 0.5)
                faded += 1
            else:
                # Isolated themes fade.
                new_amp = max(0.0, previous - self._AMPLIFY_DECAY)
                if previous > 0.0 and new_amp <= 0.0:
                    self._update_stats(isolated_themes_faded=1)
                faded += 1
            direction = self._classify_direction(previous, new_amp)
            theme["amplitude"] = new_amp
            theme["direction"] = direction.value
        self._record_event("phase_amplify", {
            "amplified": amplified,
            "faded": faded,
        })
        return {"amplified": amplified, "faded": faded}

    def _phase_propagate(self) -> Dict[str, Any]:
        """Propagate phase: amplified themes bleed into adjacent narrative regions."""
        propagated = 0
        # Sort themes by amplitude so the strongest themes propagate first.
        ordered = sorted(
            self._themes.items(),
            key=lambda kv: kv[1].get("amplitude", 0.0),
            reverse=True,
        )
        region_ids = list(self._regions.keys())
        for theme_id, theme in ordered:
            amplitude = theme.get("amplitude", 0.0)
            if amplitude < self._RESONANCE_UNISON_THRESHOLD:
                continue
            # Pick a few adjacent regions to bleed into.
            if not region_ids:
                break
            random.shuffle(region_ids)
            hops = min(self._MAX_PROPAGATION_HOPS, len(region_ids))
            theme_regions = theme.setdefault("regions", {})
            for hop in range(hops):
                target = region_ids[hop]
                intensity = amplitude * (self._PROPAGATION_DECAY ** (hop + 1))
                intensity = max(0.0, min(1.0, intensity))
                # Seed motif-level (mid) presence in the target region.
                current = self._regions.get(target, 0.0)
                self._regions[target] = min(1.0, current + intensity * 0.2)
                theme_regions[target] = max(
                    theme_regions.get(target, 0.0),
                    intensity,
                )
                propagated += 1
        self._update_stats(themes_propagated=propagated)
        self._record_event("phase_propagate", {"propagated": propagated})
        return {"propagated": propagated}

    def _phase_integrate(self) -> Dict[str, Any]:
        """Integrate phase: fold the propagated state back into the stratum map."""
        integrated = 0
        for theme_id, theme in self._themes.items():
            reading = self._resonance.get(theme_id)
            if reading is None:
                continue
            amplitude = theme.get("amplitude", 0.0)
            # A theme that has been amplified and propagated now gently lifts
            # its deeper strata, since propagation seeds motif-level presence.
            if amplitude > 0.0:
                lift = amplitude * 0.05
                theme["mid"] = max(0.0, min(1.0, theme.get("mid", 0.0) + lift))
                # Surface presence slowly decays toward the deeper strata so a
                # mature theme stops relying on being literally stated.
                theme["surface"] = max(0.0, theme.get("surface", 0.0) - lift * 0.5)
                integrated += 1
        # Update overall state.
        saturated = sum(
            1 for t in self._themes.values()
            if t.get("amplitude", 0.0) >= self._SATURATION_AMPLITUDE
        )
        if saturated >= 3:
            self._state = StratumState.SATURATED
        self._record_event("phase_integrate", {
            "integrated": integrated,
            "saturated": saturated,
        })
        return {"integrated": integrated, "saturated": saturated}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _classify_resonance(self, surface: float, mid: float,
                            deep: float) -> tuple:
        """Classify a theme's resonance mode and score from its stratum values."""
        values = (surface, mid, deep)
        strong = [v for v in values if v >= self._RESONANCE_UNISON_THRESHOLD]
        spread = max(values) - min(values)
        # Identify the dominant stratum.
        named = ((surface, ThemeStratum.SURFACE),
                 (mid, ThemeStratum.MID),
                 (deep, ThemeStratum.DEEP))
        dominant = max(named, key=lambda pair: pair[0])[1]
        # Dissonance: one stratum is very strong while another is near zero.
        if spread >= self._DISSONANCE_SPREAD and max(values) >= 0.6 \
                and min(values) <= 0.15:
            mode = ResonanceMode.DISSONANT
        elif len(strong) == 3:
            mode = ResonanceMode.UNISON
        elif len(strong) == 2:
            # Confirm the two strong strata are not in conflict.
            mode = ResonanceMode.PARTIAL
        elif len(strong) == 1:
            mode = ResonanceMode.ISOLATED
        else:
            # Nothing is strong; check whether two strata are at least partial.
            pair_avg = (surface + mid + deep) / 3.0
            if pair_avg >= self._RESONANCE_PARTIAL_PAIR_MIN:
                mode = ResonanceMode.PARTIAL
            else:
                mode = ResonanceMode.ISOLATED
        # Cross-stratum score rewards breadth (all three strata active)
        # and penalizes wide gaps between strata.
        breadth = (surface + mid + deep) / 3.0
        agreement = 1.0 - (spread / 1.0) if max(values) > 0 else 0.0
        score = max(0.0, min(1.0, breadth * 0.6 + agreement * 0.4))
        return mode, score, dominant

    def _classify_direction(self, previous: float, current: float) -> AmplificationDirection:
        """Classify the direction a theme's amplitude is moving."""
        delta = current - previous
        if current <= 0.01:
            return AmplificationDirection.DORMANT
        if delta > 0.02:
            return AmplificationDirection.RISING
        if delta < -0.02:
            return AmplificationDirection.FADING
        return AmplificationDirection.STEADY

    def _resonance_note(self, mode: ResonanceMode,
                        dominant: ThemeStratum) -> str:
        """Compose a short note describing the resonance reading."""
        return f"{mode.value} resonance centered on the {dominant.value} stratum"

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_resonance(self, theme_id: str) -> Dict[str, Any]:
        with self._global_lock:
            theme = self._themes.get(theme_id)
            if theme is None:
                return {"error": f"Theme not found: {theme_id}"}
            reading = self._resonance.get(theme_id)
            if reading is None:
                return {"error": f"No resonance reading for: {theme_id}"}
            return {
                "theme_id": theme_id,
                "mode": reading.mode.value,
                "cross_stratum_score": reading.cross_stratum_score,
                "dominant_stratum": reading.dominant_stratum.value,
                "amplitude": theme.get("amplitude", 0.0),
                "direction": theme.get("direction", AmplificationDirection.DORMANT.value),
                "surface": theme.get("surface", 0.0),
                "mid": theme.get("mid", 0.0),
                "deep": theme.get("deep", 0.0),
                "note": reading.note,
            }

    def get_themes(self) -> Dict[str, Any]:
        with self._global_lock:
            themes = []
            for theme_id, theme in self._themes.items():
                reading = self._resonance.get(theme_id)
                themes.append({
                    "theme_id": theme_id,
                    "surface": theme.get("surface", 0.0),
                    "mid": theme.get("mid", 0.0),
                    "deep": theme.get("deep", 0.0),
                    "amplitude": theme.get("amplitude", 0.0),
                    "direction": theme.get("direction", AmplificationDirection.DORMANT.value),
                    "mode": reading.mode.value if reading else ResonanceMode.ISOLATED.value,
                    "note": theme.get("note", ""),
                })
            return {"themes": themes, "count": len(themes)}

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "state": self._state.value,
                "cycle_count": self._cycle_count,
                "themes": len(self._themes),
                "regions": len(self._regions),
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation and Reset
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic themes and regions, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_themes()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_themes(self) -> None:
        """Seed a small synthetic field with themes spanning the strata."""
        seed_themes = [
            ("sim_loss", 0.7, 0.5, 0.3, "a literal grief stated aloud"),
            ("sim_renewal", 0.4, 0.6, 0.5, "a recurring spring motif"),
            ("sim_betrayal", 0.8, 0.3, 0.2, "a stated grievance"),
            ("sim_shadow", 0.2, 0.5, 0.7, "an archetype felt at the edges"),
            ("sim_dawning", 0.5, 0.5, 0.5, "a theme balanced across strata"),
        ]
        for theme_id, s, m, d, note in seed_themes:
            if theme_id not in self._themes:
                self.register_theme(theme_id, note=note)
            self.set_theme_presence(theme_id, surface=s, mid=m, deep=d)
        # Seed a few narrative regions for propagation to bleed into.
        seed_regions = ["sim_act_one", "sim_act_two", "sim_act_three",
                        "sim_epilogue"]
        for region_id in seed_regions:
            if region_id not in self._regions and \
                    len(self._regions) < self._MAX_REGIONS:
                self._regions[region_id] = 0.0

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._themes.clear()
            self._resonance.clear()
            self._regions.clear()
            self._events_log.clear()
            self._phase = ResonancePhase.STRATIFY
            self._state = StratumState.STRATIFYING
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
