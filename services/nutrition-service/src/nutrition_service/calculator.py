from __future__ import annotations

from collections import defaultdict

from nutrition_service.models import (
    DISCLAIMER,
    DailyValue,
    FoodReference,
    MealItemRequest,
    MealItemResult,
    MicronutrientResult,
    NutritionAnalysis,
)


MICRONUTRIENT_KEYS = [
    ("fiber_g", "g"),
    ("sodium_mg", "mg"),
    ("potassium_mg", "mg"),
    ("vitamin_c_mg", "mg"),
    ("iron_mg", "mg"),
]


def scale_food(reference: FoodReference, portion_multiplier: float) -> dict[str, float]:
    return {
        "calories": reference.calories * portion_multiplier,
        "protein_g": reference.protein_g * portion_multiplier,
        "carbs_g": reference.carbs_g * portion_multiplier,
        "fat_g": reference.fat_g * portion_multiplier,
        "fiber_g": reference.fiber_g * portion_multiplier,
        "sodium_mg": reference.sodium_mg * portion_multiplier,
        "potassium_mg": reference.potassium_mg * portion_multiplier,
        "vitamin_c_mg": reference.vitamin_c_mg * portion_multiplier,
        "iron_mg": reference.iron_mg * portion_multiplier,
    }


def macro_percentages(protein_g: float, carbs_g: float, fat_g: float) -> dict[str, dict[str, float]]:
    protein_kcal = protein_g * 4
    carbs_kcal = carbs_g * 4
    fat_kcal = fat_g * 9
    total = protein_kcal + carbs_kcal + fat_kcal
    if total == 0:
        return {
            "protein": {"grams": 0.0, "kcal": 0.0, "percent_of_calories": 0.0},
            "carbs": {"grams": 0.0, "kcal": 0.0, "percent_of_calories": 0.0},
            "fat": {"grams": 0.0, "kcal": 0.0, "percent_of_calories": 0.0},
        }

    return {
        "protein": {
            "grams": round(protein_g, 1),
            "kcal": round(protein_kcal, 1),
            "percent_of_calories": round((protein_kcal / total) * 100, 1),
        },
        "carbs": {
            "grams": round(carbs_g, 1),
            "kcal": round(carbs_kcal, 1),
            "percent_of_calories": round((carbs_kcal / total) * 100, 1),
        },
        "fat": {
            "grams": round(fat_g, 1),
            "kcal": round(fat_kcal, 1),
            "percent_of_calories": round((fat_kcal / total) * 100, 1),
        },
    }


def build_insights(calories: float, protein_g: float, fiber_g: float, sodium_mg: float) -> list[str]:
    insights: list[str] = []
    if protein_g >= 25:
        insights.append("This meal appears relatively high in protein for general wellness tracking.")
    if fiber_g >= 5:
        insights.append("This meal likely contributes a meaningful amount of dietary fiber.")
    if sodium_mg >= 700:
        insights.append("This meal may be higher in sodium, so serving size can materially affect the estimate.")
    if calories < 250:
        insights.append("This appears to be a lighter meal or snack based on the estimated portion.")
    if not insights:
        insights.append("Portion size and preparation style can change the final nutrition estimate.")
    return insights


def analyze_meal(
    requests: list[MealItemRequest],
    references: dict[str, FoodReference],
    daily_values: dict[str, DailyValue],
    requires_user_clarification: bool = False,
) -> NutritionAnalysis:
    totals = defaultdict(float)
    meal_items: list[MealItemResult] = []
    provenance: list[dict[str, str]] = []

    for request in requests:
        reference = references[request.food_code]
        scaled = scale_food(reference, request.portion_multiplier)
        for key, value in scaled.items():
            totals[key] += value
        meal_items.append(
            MealItemResult(
                food_code=reference.food_code,
                description=reference.description,
                portion_multiplier=request.portion_multiplier,
                estimated_calories=round(scaled["calories"], 1),
                protein_g=round(scaled["protein_g"], 1),
                carbs_g=round(scaled["carbs_g"], 1),
                fat_g=round(scaled["fat_g"], 1),
            )
        )
        provenance.append(
            {
                "food_code": reference.food_code,
                "source_name": reference.source_name,
                "source_version": reference.source_version,
            }
        )

    micronutrients = []
    for nutrient_key, unit in MICRONUTRIENT_KEYS:
        value = totals[nutrient_key]
        daily_value = daily_values.get(nutrient_key)
        percent = 0.0
        label = nutrient_key
        if daily_value:
            percent = round((value / daily_value.amount) * 100, 1) if daily_value.amount else 0.0
            label = daily_value.label
        micronutrients.append(
            MicronutrientResult(
                nutrient_key=nutrient_key,
                label=label,
                amount=round(value, 1),
                unit=unit,
                percent_daily_value=percent,
            )
        )

    macros = macro_percentages(totals["protein_g"], totals["carbs_g"], totals["fat_g"])
    safety_flags = ["requires_clarification"] if requires_user_clarification else []
    return NutritionAnalysis(
        meal_items=meal_items,
        estimated_calories=round(totals["calories"], 1),
        macros=macros,
        micronutrients=micronutrients,
        insights=build_insights(
            totals["calories"],
            totals["protein_g"],
            totals["fiber_g"],
            totals["sodium_mg"],
        ),
        confidence="medium" if requires_user_clarification else "high",
        disclaimer=DISCLAIMER,
        safety_flags=safety_flags,
        requires_user_clarification=requires_user_clarification,
        source_provenance=provenance,
    )

