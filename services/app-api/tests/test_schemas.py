from __future__ import annotations

import unittest

from app_api.schemas import (
    InferenceEnvelope,
    InferencePayload,
    MealItem,
    ModerationEnvelope,
    ModerationPayload,
    ObserverEnvelope,
    ObserverPayload,
    OutputReviewEnvelope,
    OutputReviewPayload,
    OutputSafetyReviewPayload,
    QuestionAnswerEnvelope,
    QuestionAnswerPayload,
    QuestionSafety,
    TimingBreakdown,
    USDAFoodMatch,
    USDAFoodNutrients,
)


class SchemaTests(unittest.TestCase):
    def test_moderation_envelope_serializes(self) -> None:
        envelope = ModerationEnvelope(
            request_id="req_1",
            meal_id="meal_1",
            model="omni-moderation-latest",
            payload=ModerationPayload(
                flagged=True,
                categories=["sexual_content"],
                image_labels=["sexual_content"],
                reason="unsafe image or text",
            ),
        )

        data = envelope.model_dump()
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["stage"], "moderation")
        self.assertEqual(data["payload"]["categories"], ["sexual_content"])
        self.assertEqual(data["payload"]["flagged"], True)

    def test_inference_envelope_supports_nested_meal_items(self) -> None:
        envelope = InferenceEnvelope(
            request_id="req_2",
            meal_id="meal_2",
            model="gpt-5.4-mini",
            confidence="high",
            timings_ms=TimingBreakdown(moderation=12.5, observer=8.0, inference=24.0),
            payload=InferencePayload(
                image_labels=["food", "meal"],
                moderation_flags=[],
                food_relevance="food",
                safe_to_process=True,
                detected_components=["grilled chicken", "rice"],
                meal_items=[
                    MealItem(
                        label="grilled chicken",
                        confidence="high",
                        estimated_portion_description="about 5 oz",
                        estimated_amount=5,
                        estimated_unit="oz",
                        item_count=1,
                        usda_match=USDAFoodMatch(
                            fdc_id=12345,
                            description="Chicken, roasted",
                            data_type="Foundation",
                            nutrients=USDAFoodNutrients(calories=165, protein_g=31),
                        ),
                    )
                ],
            ),
        )

        data = envelope.model_dump()
        self.assertEqual(data["stage"], "inference")
        self.assertEqual(data["timings_ms"]["observer"], 8.0)
        self.assertEqual(data["payload"]["detected_components"], ["grilled chicken", "rice"])
        self.assertEqual(data["payload"]["meal_items"][0]["usda_match"]["fdc_id"], 12345)

    def test_q_and_a_envelope_carries_safety(self) -> None:
        envelope = QuestionAnswerEnvelope(
            request_id="req_3",
            meal_id="meal_3",
            model="gpt-5.4-mini",
            payload=QuestionAnswerPayload(
                question="Which item has the most protein?",
                answer="The grilled chicken contributes the most protein.",
                disclaimer="These values are estimates.",
                safety=QuestionSafety(is_safe=True, notes="General nutrition wording only"),
            ),
        )

        data = envelope.model_dump()
        self.assertEqual(data["stage"], "qa")
        self.assertEqual(data["payload"]["safety"]["is_safe"], True)
        self.assertEqual(data["payload"]["question"], "Which item has the most protein?")

    def test_output_review_envelope_is_simple(self) -> None:
        envelope = OutputReviewEnvelope(
            request_id="req_4",
            meal_id="meal_4",
            model="gpt-5.4-nano",
            payload=OutputReviewPayload(is_safe=True, notes="General wellness wording."),
        )

        data = envelope.model_dump()
        self.assertEqual(data["stage"], "output_review")
        self.assertEqual(data["payload"]["is_safe"], True)

    def test_output_safety_review_payload(self) -> None:
        payload = OutputSafetyReviewPayload(
            is_safe=True,
            answer="This is general nutrition information only.",
        )
        self.assertEqual(payload.model_dump()["is_safe"], True)
        self.assertIn("nutrition", payload.answer)


class ObserverSchemaTests(unittest.TestCase):
    def test_observer_envelope(self) -> None:
        envelope = ObserverEnvelope(
            request_id="req_5",
            meal_id="meal_5",
            model="gpt-5.4-nano",
            payload=ObserverPayload(
                food_relevance="food",
                image_labels=["food", "plate"],
                requires_user_clarification=False,
                observer_notes="Looks like a plated meal.",
            ),
        )

        data = envelope.model_dump()
        self.assertEqual(data["stage"], "observer")
        self.assertEqual(data["payload"]["food_relevance"], "food")
        self.assertEqual(data["payload"]["image_labels"], ["food", "plate"])


if __name__ == "__main__":
    unittest.main()
