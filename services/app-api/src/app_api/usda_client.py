from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app_api.schemas import USDAFoodDetailsResponse, USDAFoodSearchResponse, USDAFoodSearchItem, USDAFoodNutrients


USDA_API_BASE = os.environ.get("USDA_API_BASE", "https://api.nal.usda.gov/fdc/v1")
USDA_API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")

NUTRIENT_ALIASES = {
    "calories": ["Energy", "Energy (Atwater General Factors)", "Metabolizable Energy (Atwater General Factor)"],
    "protein_g": ["Protein"],
    "carbs_g": ["Carbohydrate, by difference"],
    "fat_g": ["Total lipid (fat)"],
    "fiber_g": ["Fiber, total dietary"],
    "sodium_mg": ["Sodium, Na"],
    "potassium_mg": ["Potassium, K"],
    "iron_mg": ["Iron, Fe"],
    "vitamin_c_mg": ["Vitamin C, total ascorbic acid"],
}


class USDAFoodDataClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or USDA_API_KEY
        self.base_url = (base_url or USDA_API_BASE).rstrip("/")

    def search_foods(self, query: str, limit: int = 5) -> USDAFoodSearchResponse:
        payload = self._post(
            "/foods/search",
            {
                "query": query,
                "pageSize": max(1, min(limit, 10)),
            },
        )
        foods = payload.get("foods", [])
        return USDAFoodSearchResponse(
            query=query,
            items=[
                USDAFoodSearchItem(
                    fdc_id=food.get("fdcId"),
                    description=food.get("description"),
                    data_type=food.get("dataType"),
                    brand_owner=food.get("brandOwner"),
                )
                for food in foods
            ],
        )

    def get_food_details(self, fdc_id: int) -> USDAFoodDetailsResponse:
        payload = self._get(f"/food/{fdc_id}")
        nutrients = self._extract_nutrients(payload.get("foodNutrients", []))
        return USDAFoodDetailsResponse(
            fdc_id=payload.get("fdcId"),
            description=payload.get("description"),
            data_type=payload.get("dataType"),
            brand_owner=payload.get("brandOwner"),
            serving_size=payload.get("servingSize"),
            serving_size_unit=payload.get("servingSizeUnit"),
            household_serving_fulltext=payload.get("householdServingFullText"),
            food_portions=payload.get("foodPortions", []),
            nutrients=USDAFoodNutrients.model_validate(nutrients),
            source="USDA FoodData Central",
        )

    def _extract_nutrients(self, nutrient_rows: list[dict[str, Any]]) -> dict[str, Any]:
        extracted: dict[str, Any] = {}
        for key, aliases in NUTRIENT_ALIASES.items():
            extracted[key] = self._find_nutrient_value(nutrient_rows, aliases)
        return extracted

    def _find_nutrient_value(self, nutrient_rows: list[dict[str, Any]], aliases: list[str]) -> float | None:
        for row in nutrient_rows:
            nutrient = row.get("nutrient", {})
            name = nutrient.get("name") or row.get("name")
            if name in aliases:
                return row.get("amount")
        return None

    def _get(self, path: str) -> dict[str, Any]:
        query = urlencode({"api_key": self.api_key})
        request = Request(f"{self.base_url}{path}?{query}", headers={"Accept": "application/json"})
        return self._read_json(request)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        query = urlencode({"api_key": self.api_key})
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}?{query}",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._read_json(request)

    def _read_json(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8")
                try:
                    return json.loads(body)
                except json.JSONDecodeError as error:
                    preview = body[:300] if body else "<empty>"
                    raise RuntimeError(f"USDA API returned invalid JSON: {preview}") from error
        except HTTPError as error:  # pragma: no cover
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"USDA API request failed with status {error.code}: {detail}") from error
        except URLError as error:  # pragma: no cover
            raise RuntimeError(f"USDA API request failed: {error.reason}") from error
