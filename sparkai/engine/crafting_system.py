"""
SparkLabs Engine - Crafting System

Recipe-based item crafting with ingredient requirements, quality
tiers, tool dependencies, and discovery mechanics. Supports
multi-step crafting chains, resource scarcity balancing, and
specialization bonuses for dedicated crafting characters.

Architecture:
  CraftingSystem
    |-- RecipeRegistry (crafting recipe catalog with requirements)
    |-- IngredientValidator (resource availability and quantity checks)
    |-- QualityEvaluator (crafting skill-based result quality)
    |-- DiscoveryEngine (experimental combination uncovering)
    |-- CraftingStation (station-specific recipe filtering)

Quality Tiers:
  - CRUDE: basic, minimal stats
  - STANDARD: baseline quality
  - FINE: above-average craftsmanship
  - SUPERIOR: exceptional quality
  - MASTERWORK: peak craftsmanship
  - LEGENDARY: perfect, maximum stats
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QualityTier(Enum):
    CRUDE = "crude"
    STANDARD = "standard"
    FINE = "fine"
    SUPERIOR = "superior"
    MASTERWORK = "masterwork"
    LEGENDARY = "legendary"


class CraftingCategory(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    TOOL = "tool"
    DECORATION = "decoration"
    UPGRADE = "upgrade"


@dataclass
class Ingredient:
    item_id: str
    name: str = ""
    quantity: int = 1
    is_consumed: bool = True
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "quantity": self.quantity,
            "is_consumed": self.is_consumed,
        }


@dataclass
class CraftingRecipe:
    recipe_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    category: CraftingCategory = CraftingCategory.CONSUMABLE
    ingredients: List[Ingredient] = field(default_factory=list)
    result_item_id: str = ""
    result_name: str = ""
    result_quantity: int = 1
    min_skill_level: int = 1
    crafting_time: float = 2.0
    required_station: str = ""
    required_tools: List[str] = field(default_factory=list)
    quality_thresholds: Dict[QualityTier, int] = field(default_factory=dict)
    is_hidden: bool = False
    discovery_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "name": self.name,
            "category": self.category.value,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "result": self.result_name,
            "quantity": self.result_quantity,
            "min_skill": self.min_skill_level,
            "crafting_time": self.crafting_time,
            "required_station": self.required_station,
            "is_hidden": self.is_hidden,
        }


@dataclass
class CraftingResult:
    success: bool = False
    result_item_id: str = ""
    result_name: str = ""
    quantity: int = 0
    quality: QualityTier = QualityTier.STANDARD
    xp_gained: int = 0
    ingredients_consumed: bool = True
    message: str = ""


class CraftingSystem:
    _instance: Optional[CraftingSystem] = None

    def __init__(self):
        self._recipes: Dict[str, CraftingRecipe] = {}
        self._character_skills: Dict[str, Dict[str, int]] = {}
        self._character_recipes: Dict[str, Set[str]] = {}
        self._default_quality_thresholds: Dict[QualityTier, int] = {
            QualityTier.CRUDE: 1,
            QualityTier.STANDARD: 10,
            QualityTier.FINE: 25,
            QualityTier.SUPERIOR: 50,
            QualityTier.MASTERWORK: 80,
            QualityTier.LEGENDARY: 100,
        }
        self._craft_count: int = 0

    @classmethod
    def get_instance(cls) -> CraftingSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_recipe(self, recipe: CraftingRecipe) -> str:
        if not recipe.quality_thresholds:
            recipe.quality_thresholds = dict(self._default_quality_thresholds)
        self._recipes[recipe.recipe_id] = recipe
        return recipe.recipe_id

    def get_character_skill(self, character_id: str, category: str = "all") -> int:
        skills = self._character_skills.get(character_id, {})
        if category == "all":
            return sum(skills.values())
        return skills.get(category, 1)

    def improve_skill(self, character_id: str, category: str, xp: int) -> int:
        if character_id not in self._character_skills:
            self._character_skills[character_id] = {}
        current = self._character_skills[character_id].get(category, 1)
        self._character_skills[character_id][category] = current + xp
        return self._character_skills[character_id][category]

    def learn_recipe(self, character_id: str, recipe_id: str) -> bool:
        if recipe_id not in self._recipes:
            return False
        if character_id not in self._character_recipes:
            self._character_recipes[character_id] = set()
        self._character_recipes[character_id].add(recipe_id)
        return True

    def craft(
        self,
        character_id: str,
        recipe_id: str,
        inventory: Dict[str, int],
        station: str = "",
    ) -> CraftingResult:
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return CraftingResult(message="Recipe not found")

        skill_level = self.get_character_skill(character_id, recipe.category.value)
        if skill_level < recipe.min_skill_level:
            return CraftingResult(
                message=f"Requires {recipe.category.value} skill level {recipe.min_skill_level}",
            )

        if recipe.required_station and recipe.required_station != station:
            return CraftingResult(message=f"Requires {recipe.required_station} station")

        for ingredient in recipe.ingredients:
            available = inventory.get(ingredient.item_id, 0)
            if available < ingredient.quantity:
                if not ingredient.alternatives:
                    return CraftingResult(
                        message=f"Missing {ingredient.item_id}: need {ingredient.quantity}, have {available}",
                    )
                alt_found = False
                for alt_id in ingredient.alternatives:
                    if inventory.get(alt_id, 0) >= ingredient.quantity:
                        alt_found = True
                        break
                if not alt_found:
                    return CraftingResult(
                        message=f"Missing {ingredient.item_id} (no alternatives available)",
                    )

        quality_thresholds = recipe.quality_thresholds or self._default_quality_thresholds
        quality = QualityTier.STANDARD
        for tier, threshold in sorted(quality_thresholds.items(), key=lambda x: x[1]):
            if skill_level >= threshold:
                quality = tier

        xp_gain = max(1, int(recipe.crafting_time * recipe.min_skill_level * 0.5))
        self.improve_skill(character_id, recipe.category.value, xp_gain)
        self._craft_count += 1

        return CraftingResult(
            success=True,
            result_item_id=recipe.result_item_id,
            result_name=recipe.result_name,
            quantity=recipe.result_quantity,
            quality=quality,
            xp_gained=xp_gain,
            ingredients_consumed=True,
            message=f"Crafted {quality.value} {recipe.result_name}",
        )

    def discover_recipes(
        self,
        character_id: str,
        inventory: Dict[str, int],
        skill_level: int,
    ) -> List[CraftingRecipe]:
        discovered = []
        for recipe in self._recipes.values():
            if not recipe.is_hidden:
                continue
            if recipe.min_skill_level > skill_level:
                continue
            can_discover = True
            for ingredient in recipe.ingredients:
                if inventory.get(ingredient.item_id, 0) < 1:
                    can_discover = False
                    break
            if can_discover:
                self.learn_recipe(character_id, recipe.recipe_id)
                discovered.append(recipe)
        return discovered

    def get_available_recipes(
        self,
        character_id: str,
        station: str = "",
        category: Optional[CraftingCategory] = None,
    ) -> List[CraftingRecipe]:
        known = self._character_recipes.get(character_id, set())
        available = []
        for recipe in self._recipes.values():
            if recipe.is_hidden and recipe.recipe_id not in known:
                continue
            if category and recipe.category != category:
                continue
            if recipe.required_station and recipe.required_station != station:
                continue
            if recipe_id := recipe.recipe_id not in known:
                continue
            available.append(recipe)
        return available

    def get_recipe(self, recipe_id: str) -> Optional[CraftingRecipe]:
        return self._recipes.get(recipe_id)

    def get_stats(self) -> Dict[str, Any]:
        categories = {}
        for recipe in self._recipes.values():
            cat = recipe.category.value
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        return {
            "total_recipes": len(self._recipes),
            "total_crafts": self._craft_count,
            "hidden_recipes": sum(1 for r in self._recipes.values() if r.is_hidden),
            "categories": categories,
            "crafters": len(self._character_skills),
        }


def get_crafting_system() -> CraftingSystem:
    return CraftingSystem.get_instance()