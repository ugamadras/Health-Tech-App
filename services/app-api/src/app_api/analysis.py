from __future__ import annotations

from typing import Any, Protocol

from app_api.models import MealRecord, UploadRequest, VisionInference
from app_api.policy import validate_upload
from app_api.schemas import MealAnalysisPayload, MealItem, NutritionSummary, NutritionTotals
from app_api.storage import InMemoryMealStore


UNIT_TO_GRAMS = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "lb": 453.592,
    "pound": 453.592,
    "pounds": 453.592,
}


class VisionClient(Protocol):
    def analyze_upload(self, upload: UploadRequest) -> VisionInference:
        ...

    def answer_question(self, meal_record: MealRecord, question: str) -> dict:
        ...


class MealAnalysisOrchestrator:
    def __init__(self, store: InMemoryMealStore, vision_client: VisionClient | None = None):
        self.store = store
        self.vision_client = vision_client

    def create_meal(self, user_id: str, upload: UploadRequest) -> MealRecord:
        model_analysis = None
        if self.vision_client is not None and upload.image_base64:
            model_analysis = self.vision_client.analyze_upload(upload)
            upload = upload.model_copy(update={"image_labels": model_analysis.image_labels or upload.image_labels})

        validation = validate_upload(upload)
        detected_components = model_analysis.detected_components if model_analysis is not None else []
        has_detected_items = bool(detected_components or (model_analysis.meal_items if model_analysis is not None else []))
        if (
            model_analysis is not None
            and model_analysis.safe_to_process
            and (model_analysis.food_relevance == "food" or has_detected_items)
            and validation.status != "rejected"
        ):
            validation = validation.model_copy(
                update={
                    "status": "accepted",
                    "reason_code": "accepted",
                    "safe_to_process": True,
                    "food_relevance": "food",
                }
            )

        status = validation.status
        analysis: MealAnalysisPayload | None = None

        if validation.safe_to_process and has_detected_items:
            status = "completed" if validation.status == "accepted" else "needs_clarification"
            meal_items = model_analysis.meal_items if model_analysis is not None else []
            analysis = MealAnalysisPayload(
                detected_components=detected_components,
                meal_items=meal_items,
                nutrition_summary=self._build_nutrition_summary(meal_items),
            )
        elif validation.safe_to_process:
            status = "needs_clarification"
            if validation.status == "accepted":
                validation = validation.model_copy(
                    update={
                        "status": "needs_clarification",
                        "reason_code": "missing_meal_items",
                        "food_relevance": "uncertain",
                    }
                )

        record = MealRecord(
            meal_id=self.store.next_id(),
            user_id=user_id,
            status=status,
            validation=validation,
            analysis=analysis,
            detected_components=detected_components,
            model_response=model_analysis.raw_response if model_analysis is not None else None,
        )
        return self.store.create(record)

    def get_meal(self, meal_id: str) -> MealRecord | None:
        return self.store.get(meal_id)

    def list_meals(self, user_id: str) -> list[MealRecord]:
        return self.store.list_for_user(user_id)

    def export_meal(self, meal_id: str) -> dict:
        record = self.get_meal(meal_id)
        if record is None:
            raise KeyError(meal_id)
        return {
            "meal_id": record.meal_id,
            "format": "json",
            "payload": record.to_dict(),
        }

    def answer_meal_question(self, meal_id: str, question: str) -> dict:
        record = self.get_meal(meal_id)
        if record is None:
            raise KeyError(meal_id)
        if not question.strip():
            raise ValueError("Question is required")
        if self.vision_client is not None and hasattr(self.vision_client, "answer_question"):
            return self.vision_client.answer_question(record, question)
        return self._fallback_answer(record, question)

    def _build_nutrition_summary(self, meal_items: list[MealItem]) -> NutritionSummary:
        totals = NutritionTotals()
        confident_totals = NutritionTotals()
        matched_items = 0
        confident_items = 0

        for item in meal_items:
            item_data = self._meal_item_to_dict(item)
            usda_match = item.usda_match.model_dump() if item.usda_match is not None else {}
            nutrients = usda_match.get("nutrients") or {}
            if usda_match:
                matched_items += 1
            multiplier = self._estimate_portion_multiplier(item_data)
            for key in totals.model_dump().keys():
                value = nutrients.get(key)
                if value is not None:
                    scaled_value = float(value) * multiplier
                    setattr(totals, key, getattr(totals, key) + scaled_value)
                    if usda_match and self._is_confident_for_insights(item_data):
                        setattr(confident_totals, key, getattr(confident_totals, key) + scaled_value)
            if usda_match and self._is_confident_for_insights(item_data):
                confident_items += 1

        insights = self._build_user_friendly_insights(confident_totals, confident_items)

        return NutritionSummary(
            totals=totals,
            matched_item_count=matched_items,
            identified_item_count=len(meal_items),
            insights=insights,
        )

    def _build_user_friendly_insights(self, totals: NutritionTotals, confident_items: int) -> list[str]:
        if confident_items <= 0:
            return [
                "We identified likely food items, but portions were not confident enough for detailed meal insights.",
                "These numbers are best used as broad estimates. A clearer top-down photo can improve detail.",
            ]

        insights: list[str] = []

        if totals.calories > 0:
            insights.append(f"Based on the clearest items and portions, this meal is estimated at about {round(totals.calories)} calories.")

        macro_calories = {
            "protein": max(0.0, totals.protein_g) * 4.0,
            "carbs": max(0.0, totals.carbs_g) * 4.0,
            "fat": max(0.0, totals.fat_g) * 9.0,
        }
        total_macro_calories = sum(macro_calories.values())
        if total_macro_calories > 0:
            dominant_macro = max(macro_calories, key=macro_calories.get)
            dominant_share = round((macro_calories[dominant_macro] / total_macro_calories) * 100)
            insights.append(f"Most of the estimated calories come from {dominant_macro} (about {dominant_share}%).")

        if totals.protein_g >= 25:
            insights.append("This meal looks like a solid protein source.")
        if totals.fiber_g >= 5:
            insights.append("This meal likely provides a meaningful amount of fiber.")
        if totals.sodium_mg >= 600:
            insights.append("Estimated sodium looks on the higher side for one meal.")

        if not insights:
            insights.append("We identified the meal and generated high-level nutrition estimates.")
        return insights

    def _meal_item_to_dict(self, item: MealItem | dict[str, Any]) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump()
        return dict(item)

    def _estimate_portion_multiplier(self, item: dict[str, Any]) -> float:
        usda_match = item.get("usda_match") or {}
        serving_size = usda_match.get("serving_size")
        serving_size_unit = (usda_match.get("serving_size_unit") or "").strip().lower()
        estimated_amount = item.get("estimated_amount")
        estimated_unit = (item.get("estimated_unit") or "").strip().lower()
        item_count_multiplier = self._estimate_item_count_multiplier(item)

        if estimated_amount in (None, 0) or not estimated_unit:
            return item_count_multiplier

        try:
            estimated_amount = float(estimated_amount)
        except (TypeError, ValueError):
            return item_count_multiplier

        if serving_size and serving_size_unit and estimated_unit == serving_size_unit:
            try:
                serving_size = float(serving_size)
                if serving_size > 0:
                    return item_count_multiplier * max(0.1, estimated_amount / serving_size)
            except (TypeError, ValueError):
                return item_count_multiplier

        if estimated_unit in UNIT_TO_GRAMS and serving_size_unit in UNIT_TO_GRAMS and serving_size:
            try:
                serving_size = float(serving_size)
                estimated_grams = estimated_amount * UNIT_TO_GRAMS[estimated_unit]
                serving_grams = serving_size * UNIT_TO_GRAMS[serving_size_unit]
                if serving_grams > 0:
                    return item_count_multiplier * max(0.1, estimated_grams / serving_grams)
            except (TypeError, ValueError):
                return item_count_multiplier

        return item_count_multiplier

    def _estimate_item_count_multiplier(self, item: dict) -> float:
        item_count = item.get("item_count")
        if item_count in (None, 0):
            return 1.0
        try:
            return max(1.0, float(item_count))
        except (TypeError, ValueError):
            return 1.0

    def _is_confident_for_insights(self, item: dict[str, Any]) -> bool:
        item_confidence = str(item.get("confidence") or "").lower()
        portion_confidence = str(item.get("portion_confidence") or "").lower()
        if item_confidence not in {"medium", "high"}:
            return False
        if portion_confidence not in {"medium", "high"}:
            return False

        item_count = item.get("item_count")
        item_count_confidence = str(item.get("item_count_confidence") or "").lower()
        if item_count not in (None, 0, 1) and item_count_confidence not in {"medium", "high"}:
            return False
        return True

    def _fallback_answer(self, record: MealRecord, question: str) -> dict:
        summary = record.analysis.nutrition_summary if record.analysis is not None else None
        totals = summary.totals if summary is not None else NutritionTotals()
        answer = (
            f"Meal summary: about {round(float(totals.calories or 0))} calories, "
            f"{round(float(totals.protein_g or 0), 1)} g protein, "
            f"{round(float(totals.carbs_g or 0), 1)} g carbs, and "
            f"{round(float(totals.fat_g or 0), 1)} g fat. "
            "These values are general informational estimates based on USDA-matched items."
        )
        return {
            "question": question,
            "answer": f"{answer}\n\nDisclaimer: {record.disclaimer}",
            "disclaimer": record.disclaimer,
        }
