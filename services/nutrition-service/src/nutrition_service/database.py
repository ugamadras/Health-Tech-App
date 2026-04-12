from __future__ import annotations

import sqlite3
from pathlib import Path

from nutrition_service.models import DailyValue, FoodReference


class NutritionDatabase:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_food(self, food_code: str) -> FoodReference | None:
        connection = self._connect()
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM foods WHERE food_code = ?",
            (food_code,),
        ).fetchone()
        connection.close()
        if row is None:
            return None
        return FoodReference(**dict(row))

    def get_daily_values(self) -> dict[str, DailyValue]:
        connection = self._connect()
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT nutrient_key, label, amount, unit FROM daily_values").fetchall()
        connection.close()
        return {row["nutrient_key"]: DailyValue(**dict(row)) for row in rows}

    def search_foods(self, query: str, limit: int = 5) -> list[FoodReference]:
        normalized = query.strip().lower()
        if not normalized:
            return []

        connection = self._connect()
        connection.row_factory = sqlite3.Row
        like_query = f"%{normalized}%"
        rows = connection.execute(
            """
            SELECT * FROM foods
            WHERE lower(description) LIKE ? OR lower(food_code) LIKE ?
            ORDER BY description ASC
            LIMIT ?
            """,
            (like_query, like_query, limit),
        ).fetchall()
        connection.close()
        return [FoodReference(**dict(row)) for row in rows]
