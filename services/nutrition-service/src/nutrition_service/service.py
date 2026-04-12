from __future__ import annotations

from nutrition_service.calculator import analyze_meal
from nutrition_service.database import NutritionDatabase
from nutrition_service.models import MealItemRequest


class NutritionService:
    def __init__(self, database: NutritionDatabase):
        self.database = database

    def lookup(self, food_code: str) -> dict:
        reference = self.database.get_food(food_code)
        if reference is None:
            raise KeyError(f"Unknown food code: {food_code}")
        return {
            "food_code": reference.food_code,
            "description": reference.description,
            "source_name": reference.source_name,
            "source_version": reference.source_version,
        }

    def search(self, query: str, limit: int = 5) -> dict:
        results = self.database.search_foods(query, limit=limit)
        return {
            "query": query,
            "items": [
                {
                    "food_code": item.food_code,
                    "description": item.description,
                    "portion_grams": item.portion_grams,
                    "source_name": item.source_name,
                    "source_version": item.source_version,
                }
                for item in results
            ],
        }

    def analyze(self, meal_items: list[dict], requires_user_clarification: bool = False) -> dict:
        references = {}
        requests = []
        for item in meal_items:
            request = MealItemRequest(
                food_code=item["food_code"],
                portion_multiplier=float(item.get("portion_multiplier", 1.0)),
            )
            reference = self.database.get_food(request.food_code)
            if reference is None:
                raise KeyError(f"Unknown food code: {request.food_code}")
            references[request.food_code] = reference
            requests.append(request)

        analysis = analyze_meal(
            requests=requests,
            references=references,
            daily_values=self.database.get_daily_values(),
            requires_user_clarification=requires_user_clarification,
        )
        return analysis.to_dict()
