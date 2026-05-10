"""
SparkLabs Agent - Style Transfer Engine

Cross-domain style transfer for game assets and narrative content.
Enables transformation of visual, textual, and mechanical styles
between game elements, maintaining structural integrity while
adapting aesthetic and tonal qualities.

Architecture:
  StyleTransferEngine
    |-- StyleRegistry (catalog of registered style profiles)
    |-- TransferPipeline (multi-stage style application)
    |-- CoherenceValidator (post-transfer integrity checks)
    |-- AdaptationMatrix (cross-domain mapping rules)

Domains:
  - VISUAL: sprite, texture, color palette transformation
  - NARRATIVE: tone, voice, genre adaptation
  - MECHANICAL: rule system stylistic reinterpretation
  - AUDITORY: sound profile, music genre mapping
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StyleDomain(Enum):
    VISUAL = "visual"
    NARRATIVE = "narrative"
    MECHANICAL = "mechanical"
    AUDITORY = "auditory"


class TransferIntensity(Enum):
    SUBTLE = "subtle"
    MODERATE = "moderate"
    DRAMATIC = "dramatic"
    COMPLETE = "complete"


@dataclass
class StyleProfile:
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    domain: StyleDomain = StyleDomain.VISUAL
    attributes: Dict[str, Any] = field(default_factory=dict)
    color_palette: List[str] = field(default_factory=list)
    mood_tags: List[str] = field(default_factory=list)
    complexity: float = 1.0
    coherence_score: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "domain": self.domain.value,
            "attributes": self.attributes,
            "color_palette": self.color_palette,
            "mood_tags": self.mood_tags,
            "complexity": self.complexity,
            "coherence_score": self.coherence_score,
        }


@dataclass
class TransferResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_profile_id: str = ""
    target_content: Dict[str, Any] = field(default_factory=dict)
    transformed_content: Dict[str, Any] = field(default_factory=dict)
    applied_style_id: str = ""
    intensity: TransferIntensity = TransferIntensity.MODERATE
    coherence_score: float = 0.0
    attribute_changes: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = __import__("time").time()


@dataclass
class AdaptationRule:
    source_domain: StyleDomain
    target_domain: StyleDomain
    attribute_mapping: Dict[str, str] = field(default_factory=dict)
    intensity_factor: float = 1.0
    preserve_structure: bool = True


class StyleTransferEngine:
    _instance: Optional[StyleTransferEngine] = None

    def __init__(self):
        self._styles: Dict[str, StyleProfile] = {}
        self._rules: List[AdaptationRule] = []
        self._transfer_history: List[TransferResult] = []
        self._transfer_count: int = 0

        self._initialize_default_rules()

    @classmethod
    def get_instance(cls) -> StyleTransferEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_rules(self):
        visual_to_narrative = AdaptationRule(
            source_domain=StyleDomain.VISUAL,
            target_domain=StyleDomain.NARRATIVE,
            attribute_mapping={
                "brightness": "tone",
                "saturation": "intensity",
                "contrast": "dramatic_tension",
            },
        )
        self._rules.append(visual_to_narrative)

        narrative_to_visual = AdaptationRule(
            source_domain=StyleDomain.NARRATIVE,
            target_domain=StyleDomain.VISUAL,
            attribute_mapping={
                "tone": "brightness",
                "pacing": "contrast",
                "mood": "color_palette",
            },
        )
        self._rules.append(narrative_to_visual)

    def register_style(self, profile: StyleProfile) -> str:
        self._styles[profile.profile_id] = profile
        return profile.profile_id

    def list_styles(self, domain: Optional[StyleDomain] = None) -> List[StyleProfile]:
        if domain:
            return [s for s in self._styles.values() if s.domain == domain]
        return list(self._styles.values())

    def transfer_style(
        self,
        source_profile_id: str,
        target_content: Dict[str, Any],
        target_domain: StyleDomain,
        intensity: TransferIntensity = TransferIntensity.MODERATE,
    ) -> Optional[TransferResult]:
        source = self._styles.get(source_profile_id)
        if source is None:
            return None

        intensity_factors = {
            TransferIntensity.SUBTLE: 0.25,
            TransferIntensity.MODERATE: 0.5,
            TransferIntensity.DRAMATIC: 0.75,
            TransferIntensity.COMPLETE: 1.0,
        }
        factor = intensity_factors.get(intensity, 0.5)

        rule = self._find_adaptation_rule(source.domain, target_domain)
        if rule is None:
            rule = self._create_default_rule(source.domain, target_domain)

        transformed = dict(target_content)
        attribute_changes = {}

        for source_attr, target_attr in rule.attribute_mapping.items():
            if source_attr in source.attributes:
                source_value = source.attributes[source_attr]
                if isinstance(source_value, (int, float)):
                    transformed[target_attr] = source_value * factor * rule.intensity_factor
                elif isinstance(source_value, str):
                    transformed[target_attr] = source_value
                attribute_changes[target_attr] = {
                    "from": target_content.get(target_attr),
                    "to": transformed[target_attr],
                }

        coherence = self._evaluate_coherence(source, transformed, target_domain)

        result = TransferResult(
            source_profile_id=source_profile_id,
            target_content=target_content,
            transformed_content=transformed,
            applied_style_id=source_profile_id,
            intensity=intensity,
            coherence_score=coherence,
            attribute_changes=attribute_changes,
        )
        self._transfer_history.append(result)
        self._transfer_count += 1
        return result

    def _find_adaptation_rule(
        self, source: StyleDomain, target: StyleDomain
    ) -> Optional[AdaptationRule]:
        for rule in self._rules:
            if rule.source_domain == source and rule.target_domain == target:
                return rule
        return None

    def _create_default_rule(
        self, source: StyleDomain, target: StyleDomain
    ) -> AdaptationRule:
        return AdaptationRule(
            source_domain=source,
            target_domain=target,
            attribute_mapping={"mood": "mood", "complexity": "complexity"},
        )

    def _evaluate_coherence(
        self,
        source: StyleProfile,
        transformed: Dict[str, Any],
        target_domain: StyleDomain,
    ) -> float:
        base = source.coherence_score
        if target_domain != source.domain:
            base *= 0.7
        return min(1.0, max(0.0, base))

    def get_transfer_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in self._transfer_history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_styles": len(self._styles),
            "total_transfers": self._transfer_count,
            "adaptation_rules": len(self._rules),
            "domains": set(s.domain.value for s in self._styles.values()),
        }


def get_style_transfer() -> StyleTransferEngine:
    return StyleTransferEngine.get_instance()