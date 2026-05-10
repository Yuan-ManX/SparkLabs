"""
SparkLabs Agent - Entity Extraction Engine

Natural language game description parser that extracts structured
game world entities, relationships, and mechanics. Transforms
freeform game concept descriptions into machine-readable game
design documents ready for AI-native game generation.

Architecture:
  EntityExtractor
    |-- EntityClassifier (type detection and categorization)
    |-- RelationshipMapper (entity interconnection graph)
    |-- MechanicDetector (gameplay rule extraction)
    |-- WorldModelBuilder (composite game world assembly)
    |-- SchemaValidator (structural integrity checking)

Entity Types:
  - CHARACTER: player avatars, NPCs, enemies
  - ITEM: collectibles, equipment, consumables
  - LOCATION: levels, zones, areas, rooms
  - MECHANIC: rules, systems, interactions
  - QUEST: mission definitions and objectives
  - ABILITY: skills, powers, spells
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class EntityType(Enum):
    CHARACTER = "character"
    ITEM = "item"
    LOCATION = "location"
    MECHANIC = "mechanic"
    QUEST = "quest"
    ABILITY = "ability"
    EVENT = "event"
    UNKNOWN = "unknown"


@dataclass
class EntityAttribute:
    name: str
    value: Any
    data_type: str = "string"


@dataclass
class ExtractedEntity:
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    entity_type: EntityType = EntityType.UNKNOWN
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_text: str = ""


@dataclass
class EntityRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    description: str = ""
    strength: float = 1.0


@dataclass
class GameWorldModel:
    model_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    entities: Dict[str, ExtractedEntity] = field(default_factory=dict)
    relationships: List[EntityRelationship] = field(default_factory=list)
    extracted_mechanics: List[str] = field(default_factory=list)
    source_text: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "title": self.title,
            "entity_count": len(self.entities),
            "entities": [
                {
                    "entity_id": e.entity_id,
                    "name": e.name,
                    "type": e.entity_type.value,
                    "description": e.description,
                    "attributes": e.attributes,
                }
                for e in self.entities.values()
            ],
            "relationship_count": len(self.relationships),
            "mechanics": self.extracted_mechanics,
        }


class EntityExtractor:
    """
    Natural language entity extraction for building structured
    game world models from freeform descriptions.
    """

    _instance: Optional[EntityExtractor] = None

    @classmethod
    def get_instance(cls) -> EntityExtractor:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._models: List[GameWorldModel] = []
        self._extraction_count: int = 0
        self._entity_signals: Dict[EntityType, List[str]] = {
            EntityType.CHARACTER: [
                "player", "character", "npc", "enemy", "boss", "hero",
                "villain", "companion", "ally", "foe", "creature", "monster",
            ],
            EntityType.ITEM: [
                "item", "weapon", "armor", "potion", "collectible", "key",
                "treasure", "loot", "equipment", "consumable", "artifact",
                "currency", "coin", "gem",
            ],
            EntityType.LOCATION: [
                "level", "zone", "area", "room", "world", "map", "dungeon",
                "village", "town", "city", "forest", "castle", "temple",
                "biome", "region", "terrain",
            ],
            EntityType.MECHANIC: [
                "mechanic", "system", "rule", "physics", "combat", "crafting",
                "dialogue", "quest", "puzzle", "platforming", "stealth",
            ],
            EntityType.QUEST: [
                "quest", "mission", "objective", "goal", "task", "challenge",
                "side quest", "main quest",
            ],
            EntityType.ABILITY: [
                "ability", "skill", "power", "spell", "technique", "move",
                "attack", "special", "ultimate",
            ],
        }

    def extract(
        self,
        description: str,
        title: str = "",
    ) -> GameWorldModel:
        model = GameWorldModel(title=title or "Unnamed Game", source_text=description)
        sentences = re.split(r"[.!?]+", description)
        sentences = [s.strip() for s in sentences if s.strip()]

        for sentence in sentences:
            entity_type = self._classify_entity(sentence)
            if entity_type != EntityType.UNKNOWN:
                entity = self._create_entity(sentence, entity_type)
                model.entities[entity.entity_id] = entity

        model.relationships = self._discover_relationships(model)
        model.extracted_mechanics = self._extract_mechanics(model)
        self._extraction_count += 1
        self._models.append(model)
        return model

    def _classify_entity(self, text: str) -> EntityType:
        text_lower = text.lower()
        scores: Dict[EntityType, int] = {}
        for entity_type, signals in self._entity_signals.items():
            count = sum(1 for sig in signals if sig in text_lower)
            if count > 0:
                scores[entity_type] = count
        if not scores:
            return EntityType.UNKNOWN
        return max(scores, key=scores.get)

    def _create_entity(
        self, text: str, entity_type: EntityType
    ) -> ExtractedEntity:
        words = text.split()
        name_candidates = [
            w for w in words if w[0].isupper() and not w.isupper()
        ]
        name = name_candidates[0] if name_candidates else text[:40]

        attributes: Dict[str, Any] = {}
        number_pattern = re.compile(r"\b(\d+)\b")
        numbers = number_pattern.findall(text)
        if numbers:
            attributes["numeric_references"] = [int(n) for n in numbers]

        return ExtractedEntity(
            name=name,
            entity_type=entity_type,
            description=text,
            attributes=attributes,
            source_text=text,
            confidence=0.75,
        )

    def _discover_relationships(
        self, model: GameWorldModel
    ) -> List[EntityRelationship]:
        relationships: List[EntityRelationship] = []
        entity_list = list(model.entities.values())
        for i, e1 in enumerate(entity_list):
            for e2 in entity_list[i + 1 :]:
                if e1.entity_type == EntityType.CHARACTER and e2.entity_type == EntityType.LOCATION:
                    relationships.append(
                        EntityRelationship(
                            source_id=e1.entity_id,
                            target_id=e2.entity_id,
                            relationship_type="inhabits",
                            description=f"{e1.name} is found in {e2.name}",
                        )
                    )
                elif e1.entity_type == EntityType.CHARACTER and e2.entity_type == EntityType.ITEM:
                    relationships.append(
                        EntityRelationship(
                            source_id=e1.entity_id,
                            target_id=e2.entity_id,
                            relationship_type="possesses",
                            description=f"{e1.name} wields {e2.name}",
                        )
                    )
        return relationships

    def _extract_mechanics(self, model: GameWorldModel) -> List[str]:
        mechanics: List[str] = []
        for entity in model.entities.values():
            if entity.entity_type == EntityType.MECHANIC:
                mechanics.append(entity.description)
        return mechanics

    def build_world_model(
        self,
        input_data: Union[str, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> GameWorldModel:
        if isinstance(input_data, str):
            return self.extract(input_data, title=context.get("title", "") if context else "")
        model = GameWorldModel(title="Constructed World")
        for desc in input_data:
            if isinstance(desc, dict):
                entity = ExtractedEntity(
                    name=desc.get("name", ""),
                    entity_type=EntityType(desc.get("type", "unknown")),
                    description=desc.get("description", ""),
                    attributes=desc.get("attributes", {}),
                )
                model.entities[entity.entity_id] = entity
        model.relationships = self._discover_relationships(model)
        self._extraction_count += 1
        self._models.append(model)
        return model

    def get_stats(self) -> Dict[str, Any]:
        total_entities = sum(len(m.entities) for m in self._models)
        total_relationships = sum(len(m.relationships) for m in self._models)
        return {
            "total_extractions": self._extraction_count,
            "cached_models": len(self._models),
            "total_entities_extracted": total_entities,
            "total_relationships": total_relationships,
            "entity_types": [t.value for t in EntityType],
        }

    def reset(self) -> None:
        self._models.clear()


_entity_extractor = EntityExtractor.get_instance()


def get_entity_extractor() -> EntityExtractor:
    return _entity_extractor