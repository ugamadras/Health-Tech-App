from __future__ import annotations

import uuid

from app_api.models import MealRecord


class InMemoryMealStore:
    def __init__(self) -> None:
        self._records: dict[str, MealRecord] = {}

    def create(self, record: MealRecord) -> MealRecord:
        self._records[record.meal_id] = record
        return record

    def list_for_user(self, user_id: str) -> list[MealRecord]:
        return [record for record in self._records.values() if record.user_id == user_id]

    def get(self, meal_id: str) -> MealRecord | None:
        return self._records.get(meal_id)

    def next_id(self) -> str:
        return str(uuid.uuid4())

