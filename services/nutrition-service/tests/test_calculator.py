from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from nutrition_service.database import NutritionDatabase
from nutrition_service.service import NutritionService
from scripts.import_nutrition_data import import_data


class NutritionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "nutrition.sqlite3"
        import_data(self.db_path)
        self.service = NutritionService(NutritionDatabase(self.db_path))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_analysis_returns_macros_micros_and_disclaimer(self) -> None:
        result = self.service.analyze(
            [
                {"food_code": "grilled_chicken_breast", "portion_multiplier": 1},
                {"food_code": "brown_rice_cooked", "portion_multiplier": 1},
                {"food_code": "broccoli_steamed", "portion_multiplier": 1},
            ]
        )
        self.assertAlmostEqual(result["estimated_calories"], 469.0)
        self.assertEqual(result["macros"]["protein"]["grams"], 45.7)
        self.assertEqual(result["disclaimer"].startswith("These nutrition estimates"), True)
        self.assertEqual(result["requires_user_clarification"], False)
        self.assertEqual(len(result["micronutrients"]), 5)

    def test_lookup_returns_source_provenance(self) -> None:
        result = self.service.lookup("apple_raw")
        self.assertEqual(result["food_code"], "apple_raw")
        self.assertEqual(result["source_name"], "USDA FoodData Central")

    def test_search_returns_catalog_matches(self) -> None:
        result = self.service.search("broccoli")
        self.assertEqual(result["query"], "broccoli")
        self.assertEqual(result["items"][0]["food_code"], "broccoli_steamed")


if __name__ == "__main__":
    unittest.main()
