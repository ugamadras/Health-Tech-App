from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DISCLAIMER = (
    "These nutrition estimates are for general wellness and informational purposes "
    "only. They are not medical advice and should not be used to diagnose, treat, "
    "cure, or prevent any condition."
)


@dataclass(frozen=True)
class FoodReference:
    food_code: str
    description: str
    portion_grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    sodium_mg: float
    potassium_mg: float
    vitamin_c_mg: float
    iron_mg: float
    source_name: str
    source_version: str


@dataclass(frozen=True)
class DailyValue:
    nutrient_key: str
    label: str
    amount: float
    unit: str


@dataclass(frozen=True)
class MealItemRequest:
    food_code: str
    portion_multiplier: float


@dataclass(frozen=True)
class MicronutrientResult:
    nutrient_key: str
    label: str
    amount: float
    unit: str
    percent_daily_value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MealItemResult:
    food_code: str
    description: str
    portion_multiplier: float
    estimated_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NutritionAnalysis:
    meal_items: list[MealItemResult]
    estimated_calories: float
    macros: dict[str, Any]
    micronutrients: list[MicronutrientResult]
    insights: list[str]
    confidence: str
    disclaimer: str
    safety_flags: list[str]
    requires_user_clarification: bool
    source_provenance: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["meal_items"] = [item.to_dict() for item in self.meal_items]
        payload["micronutrients"] = [item.to_dict() for item in self.micronutrients]
        return payload

