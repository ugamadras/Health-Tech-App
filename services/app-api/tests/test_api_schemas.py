from __future__ import annotations

import unittest

from app_api.schemas import AuthRequest, MealCreateRequest, MealQuestionRequest


class ApiSchemaTests(unittest.TestCase):
    def test_auth_request_accepts_blank_password(self) -> None:
        payload = AuthRequest(email="arun@example.com")
        self.assertEqual(payload.email, "arun@example.com")

    def test_meal_create_request_defaults(self) -> None:
        payload = MealCreateRequest(
            filename="meal.jpg",
            mime_type="image/jpeg",
            size_bytes=123,
        )
        self.assertEqual(payload.text, "")
        self.assertEqual(payload.image_labels, [])

    def test_question_request_defaults(self) -> None:
        payload = MealQuestionRequest()
        self.assertEqual(payload.question, "")


if __name__ == "__main__":
    unittest.main()
