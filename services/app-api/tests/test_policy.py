from __future__ import annotations

import unittest

from app_api.analysis import MealAnalysisOrchestrator
from app_api.models import MealRecord, UploadRequest, ValidationResult, VisionInference
from app_api.openai_responses import OpenAIResponsesMealAnalyzer
from app_api.policy import guard_output_insights, validate_upload
from app_api.storage import InMemoryMealStore


class FakeVisionClient:
    def analyze_upload(self, upload: UploadRequest) -> VisionInference:
        return VisionInference(
            image_labels=["food", "meal"],
            detected_components=["grilled chicken", "rice", "broccoli"],
            meal_items=[
                {
                    "label": "grilled chicken",
                    "confidence": "high",
                    "estimated_portion_description": "about 5 oz",
                    "estimated_amount": 5,
                    "estimated_unit": "oz",
                    "portion_confidence": "medium",
                    "item_count": 1,
                    "item_count_confidence": "high",
                },
                {
                    "label": "rice",
                    "confidence": "medium",
                    "estimated_portion_description": "about 1 cup",
                    "estimated_amount": 1,
                    "estimated_unit": "cup",
                    "portion_confidence": "low",
                    "item_count": 1,
                    "item_count_confidence": "medium",
                },
                {
                    "label": "broccoli",
                    "confidence": "medium",
                    "notes": "green vegetable side",
                    "estimated_portion_description": "small side",
                    "estimated_amount": None,
                    "estimated_unit": None,
                    "portion_confidence": "low",
                    "item_count": 1,
                    "item_count_confidence": "low",
                },
            ],
            moderation_flags=[],
            food_relevance="food",
            safe_to_process=True,
            requires_user_clarification=False,
            raw_response={
                "image_labels": ["food", "meal"],
                "detected_components": ["grilled chicken", "rice", "broccoli"],
                "meal_items": [
                    {"label": "grilled chicken", "confidence": "high", "estimated_portion_description": "about 5 oz", "estimated_amount": 5, "estimated_unit": "oz", "portion_confidence": "medium", "item_count": 1, "item_count_confidence": "high"},
                    {"label": "rice", "confidence": "medium", "estimated_portion_description": "about 1 cup", "estimated_amount": 1, "estimated_unit": "cup", "portion_confidence": "low", "item_count": 1, "item_count_confidence": "medium"},
                    {"label": "broccoli", "confidence": "medium", "notes": "green vegetable side", "estimated_portion_description": "small side", "estimated_amount": None, "estimated_unit": None, "portion_confidence": "low", "item_count": 1, "item_count_confidence": "low"},
                ],
                "moderation_flags": [],
                "food_relevance": "food",
                "safe_to_process": True,
                "requires_user_clarification": False,
            },
        )

    def answer_question(self, meal_record, question: str) -> dict:
        return {
            "question": question,
            "answer": "Protein mostly comes from the grilled chicken in this analysis. This is not medical advice.",
            "disclaimer": meal_record.disclaimer,
        }


class FakeEmptyVisionClient:
    def analyze_upload(self, upload: UploadRequest) -> VisionInference:
        return VisionInference(
            image_labels=["food"],
            detected_components=[],
            meal_items=[],
            moderation_flags=[],
            food_relevance="food",
            safe_to_process=True,
            requires_user_clarification=True,
            raw_response={
                "image_labels": ["food"],
                "detected_components": [],
                "meal_items": [],
                "moderation_flags": [],
                "food_relevance": "food",
                "safe_to_process": True,
                "requires_user_clarification": True,
            },
        )


class FakeUSDAClient:
    def search_foods(self, query: str, limit: int = 5) -> dict:
        return {
            "query": query,
            "items": [
                {
                    "fdc_id": 12345,
                    "description": f"{query.title()}, USDA match",
                    "data_type": "Foundation",
                    "brand_owner": None,
                }
            ][:limit],
        }

    def get_food_details(self, fdc_id: int) -> dict:
        return {
            "fdc_id": fdc_id,
            "description": "Chicken, roasted",
            "data_type": "Foundation",
            "brand_owner": None,
            "serving_size": 100,
            "serving_size_unit": "g",
            "household_serving_fulltext": "1 serving",
            "food_portions": [],
            "nutrients": {
                "calories": 165,
                "protein_g": 31,
                "carbs_g": 0,
                "fat_g": 3.6,
            },
            "source": "USDA FoodData Central",
        }


class FakeResponsesClient:
    def __init__(
        self,
        observer_output_text: str | None = None,
        inference_output_text: str | None = None,
        review_output_text: str | None = None,
        question_output_text: str | None = None,
        flagged: bool = False,
    ) -> None:
        self.observer_output_text = observer_output_text or (
            '{"food_relevance":"food","image_labels":["food","meal"],'
            '"requires_user_clarification":false,"observer_notes":"looks like a plated meal"}'
        )
        self.inference_output_text = inference_output_text or (
            '{"image_labels":["food","meal"],'
            '"moderation_flags":[],'
            '"food_relevance":"food",'
            '"safe_to_process":true,'
            '"requires_user_clarification":false,'
            '"detected_components":["grilled chicken","rice"],'
            '"meal_items":[{"label":"grilled chicken","confidence":"high","notes":null,"estimated_portion_description":"about 5 oz","estimated_amount":5,"estimated_unit":"oz","portion_confidence":"medium","item_count":1,"item_count_confidence":"high","usda_match":{"fdc_id":12345,"description":"Chicken, roasted","data_type":"Foundation","brand_owner":null,"serving_size":100,"serving_size_unit":"g","household_serving_fulltext":"1 serving","source":"USDA FoodData Central","nutrients":{"calories":165,"protein_g":31,"carbs_g":0,"fat_g":3.6,"fiber_g":0,"sodium_mg":520,"potassium_mg":256,"iron_mg":1,"vitamin_c_mg":0}}},'
            '{"label":"rice","confidence":"medium","notes":"white rice side","estimated_portion_description":"about 1 cup","estimated_amount":1,"estimated_unit":"cup","portion_confidence":"low","item_count":1,"item_count_confidence":"medium","usda_match":null}]}'
        )
        self.review_output_text = review_output_text or (
            '{"is_safe":true,"answer":"Protein mostly comes from the grilled chicken in this meal summary. This is general nutrition information only."}'
        )
        self.meal_review_output_text = (
            '{"is_safe":true,"notes":"Structured meal analysis is safe to display as general wellness information."}'
        )
        self.question_output_text = question_output_text or (
            "Protein mostly comes from the grilled chicken, based on the USDA-matched meal items."
        )
        self.calls = []
        self.responses = self
        self.moderations = self
        self.flagged = flagged
        self.inference_started = False

    def create(self, **kwargs: object) -> object:
        if "input" in kwargs and "model" in kwargs and kwargs["model"] == "omni-moderation-latest":
            self.calls.append({"moderation": kwargs})
            result = type(
                "ModerationResult",
                (),
                {
                    "flagged": self.flagged,
                    "categories": {
                        "sexual": self.flagged,
                        "violence/graphic": False,
                        "self-harm": False,
                        "hate": False,
                    },
                },
            )()
            return type("ModerationResponse", (), {"results": [result]})()

        self.calls.append({"responses": kwargs})
        model = kwargs.get("model")
        text_format = (kwargs.get("text") or {}).get("format") or {}
        format_name = text_format.get("name")
        if format_name == "meal_observer_result":
            return type("Response", (), {"output_text": self.observer_output_text})()
        if format_name == "output_safety_review_result":
            return type("Response", (), {"output_text": self.review_output_text})()
        if format_name == "meal_output_review_result":
            return type("Response", (), {"output_text": self.meal_review_output_text})()
        if kwargs.get("previous_response_id"):
            return type(
                "Response",
                (),
                {
                    "id": "resp_final",
                    "output": [],
                    "output_text": self.inference_output_text,
                },
            )()
        instructions = kwargs.get("instructions") or ""
        if "follow-up questions about a meal analysis" in instructions:
            return type("Response", (), {"output_text": self.question_output_text})()
        return type(
            "FunctionCallResponse",
            (),
            {
                "id": "resp_tool_1",
                "output": [
                    type(
                        "ToolCall",
                        (),
                        {
                            "type": "function_call",
                            "name": "search_usda_foods",
                            "call_id": "call_search_1",
                            "arguments": '{"query":"grilled chicken","limit":3}',
                        },
                    )(),
                    type(
                        "ToolCall",
                        (),
                        {
                            "type": "function_call",
                            "name": "get_usda_food_details",
                            "call_id": "call_detail_1",
                            "arguments": '{"fdc_id":12345}',
                        },
                    )(),
                ],
                "output_text": "",
            },
        )()


class UploadPolicyTest(unittest.TestCase):
    def test_rejects_unsafe_text(self) -> None:
        upload = UploadRequest(
            filename="meal.jpg",
            mime_type="image/jpeg",
            size_bytes=1000,
            text="This is explicit porn",
            image_labels=["food"],
        )
        result = validate_upload(upload)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.reason_code, "unsafe_content")

    def test_rejects_non_food_image(self) -> None:
        upload = UploadRequest(
            filename="receipt.png",
            mime_type="image/png",
            size_bytes=1000,
            image_labels=["document"],
        )
        result = validate_upload(upload)
        self.assertEqual(result.reason_code, "non_food_image")

    def test_uncertain_food_requests_clarification(self) -> None:
        upload = UploadRequest(
            filename="meal.png",
            mime_type="image/png",
            size_bytes=1000,
            image_labels=["table"],
        )
        result = validate_upload(upload)
        self.assertEqual(result.status, "needs_clarification")

    def test_output_guard_filters_medical_language(self) -> None:
        filtered = guard_output_insights(
            [
                "This can diagnose a deficiency.",
                "Portion size and preparation style can change the final estimate.",
            ]
        )
        self.assertEqual(len(filtered), 1)
        self.assertIn("Portion size", filtered[0])

    def test_orchestrator_returns_detected_components_and_model_response(self) -> None:
        orchestrator = MealAnalysisOrchestrator(
            InMemoryMealStore(),
            vision_client=FakeVisionClient(),
        )
        record = orchestrator.create_meal(
            "user-1",
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
            ),
        )
        self.assertEqual(record.status, "completed")
        self.assertEqual(record.detected_components, ["grilled chicken", "rice", "broccoli"])
        self.assertEqual(record.analysis.meal_items[0].label, "grilled chicken")
        self.assertEqual(record.model_response["food_relevance"], "food")
        self.assertIsNotNone(record.analysis.nutrition_summary)

    def test_safe_image_without_detected_components_requests_clarification(self) -> None:
        orchestrator = MealAnalysisOrchestrator(
            InMemoryMealStore(),
            vision_client=FakeEmptyVisionClient(),
        )
        record = orchestrator.create_meal(
            "user-1",
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
            ),
        )
        self.assertEqual(record.status, "needs_clarification")
        self.assertIsNone(record.analysis)
        self.assertEqual(record.validation.reason_code, "missing_meal_items")

    def test_openai_responses_analyzer_parses_model_output(self) -> None:
        fake_client = FakeResponsesClient()
        analyzer = OpenAIResponsesMealAnalyzer(client=fake_client, usda_client=FakeUSDAClient())
        result = analyzer.analyze_upload(
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
                text="grilled chicken and rice",
            )
        )
        self.assertEqual(result.food_relevance, "food")
        self.assertEqual(result.detected_components, ["grilled chicken", "rice"])
        self.assertEqual(result.meal_items[1].label, "rice")
        self.assertEqual(result.meal_items[0].estimated_unit, "oz")
        self.assertEqual(result.meal_items[0].usda_match.fdc_id, 12345)
        self.assertEqual(result.raw_response["observer"]["food_relevance"], "food")
        self.assertEqual(result.raw_response["model_output"]["safe_to_process"], True)
        self.assertEqual(result.raw_response["output_review"]["is_safe"], True)
        self.assertEqual(len(result.raw_response["tool_results"]), 2)
        self.assertEqual(len(fake_client.calls), 5)

    def test_openai_responses_analyzer_blocks_flagged_upload_before_model(self) -> None:
        fake_client = FakeResponsesClient(flagged=True)
        analyzer = OpenAIResponsesMealAnalyzer(client=fake_client, usda_client=FakeUSDAClient())
        result = analyzer.analyze_upload(
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
                text="meal",
            )
        )
        self.assertFalse(result.safe_to_process)
        self.assertEqual(result.moderation_flags, ["sexual_content"])
        self.assertEqual(len(fake_client.calls), 1)

    def test_openai_responses_analyzer_skips_inference_for_non_food_observer_result(self) -> None:
        fake_client = FakeResponsesClient(
            observer_output_text=(
                '{"food_relevance":"non_food","image_labels":["document"],'
                '"requires_user_clarification":false,"observer_notes":"looks like a document"}'
            )
        )
        analyzer = OpenAIResponsesMealAnalyzer(client=fake_client, usda_client=FakeUSDAClient())
        result = analyzer.analyze_upload(
            UploadRequest(
                filename="receipt.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
                text="receipt",
            )
        )
        self.assertEqual(result.food_relevance, "non_food")
        self.assertEqual(result.image_labels, ["document"])
        self.assertEqual(result.raw_response["observer"]["food_relevance"], "non_food")
        self.assertIsNone(result.raw_response["model_output"])
        self.assertEqual(len(fake_client.calls), 2)

    def test_openai_responses_analyzer_reviews_followup_answer_for_safety(self) -> None:
        fake_client = FakeResponsesClient(
            question_output_text="This meal could treat a deficiency because it has protein.",
            review_output_text=(
                '{"is_safe":true,"answer":"This meal appears protein-rich based on the USDA-matched items. It is general nutrition information only."}'
            ),
        )
        analyzer = OpenAIResponsesMealAnalyzer(client=fake_client, usda_client=FakeUSDAClient())
        meal_record = MealRecord(
            meal_id="meal-1",
            user_id="user-1",
            status="completed",
            validation=ValidationResult(
                status="accepted",
                reason_code="accepted",
                safe_to_process=True,
                food_relevance="food",
                moderation_flags=[],
            ),
            analysis={"nutrition_summary": {"totals": {"protein_g": 35}}},
        )
        answer = analyzer.answer_question(meal_record, "Is this a high protein meal?")
        self.assertIn("protein-rich", answer["answer"].lower())
        self.assertIn("disclaimer:", answer["answer"].lower())
        self.assertIn("timings_ms", answer)

    def test_orchestrator_promotes_uncertain_validator_result_when_model_finds_food_items(self) -> None:
        class UncertainButDetectedVisionClient:
            def analyze_upload(self, upload: UploadRequest) -> VisionInference:
                return VisionInference(
                    image_labels=["plate"],
                    detected_components=["grilled chicken", "rice", "vegetables"],
                    meal_items=[
                        {"label": "grilled chicken", "confidence": "high"},
                        {"label": "rice", "confidence": "medium"},
                    ],
                    moderation_flags=[],
                    food_relevance="food",
                    safe_to_process=True,
                    requires_user_clarification=False,
                    raw_response={
                        "observer": {"food_relevance": "food"},
                        "model_output": {
                            "detected_components": ["grilled chicken", "rice", "vegetables"],
                            "meal_items": [
                                {"label": "grilled chicken", "confidence": "high"},
                                {"label": "rice", "confidence": "medium"},
                            ],
                        },
                    },
                )

        orchestrator = MealAnalysisOrchestrator(
            InMemoryMealStore(),
            vision_client=UncertainButDetectedVisionClient(),
        )
        record = orchestrator.create_meal(
            "user-1",
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
            ),
        )
        self.assertEqual(record.status, "completed")
        self.assertEqual(record.validation.status, "accepted")
        self.assertEqual(record.validation.reason_code, "accepted")
        self.assertEqual(record.validation.food_relevance, "food")

    def test_orchestrator_builds_usda_nutrition_summary_from_meal_items(self) -> None:
        class USDANutritionVisionClient:
            def analyze_upload(self, upload: UploadRequest) -> VisionInference:
                return VisionInference(
                    image_labels=["food", "meal"],
                    detected_components=["grilled chicken", "rice"],
                    meal_items=[
                        {
                            "label": "grilled chicken",
                            "confidence": "high",
                            "estimated_portion_description": "about 5 oz",
                            "estimated_amount": 5,
                            "estimated_unit": "oz",
                            "portion_confidence": "medium",
                            "item_count": 1,
                            "item_count_confidence": "high",
                            "usda_match": {
                                "fdc_id": 12345,
                                "description": "Chicken, roasted",
                                "data_type": "Foundation",
                                "brand_owner": None,
                                "serving_size": 100,
                                "serving_size_unit": "g",
                                "household_serving_fulltext": "1 serving",
                                "source": "USDA FoodData Central",
                                "nutrients": {
                                    "calories": 165,
                                    "protein_g": 31,
                                    "carbs_g": 0,
                                    "fat_g": 3.6,
                                    "fiber_g": 0,
                                    "sodium_mg": 520,
                                    "potassium_mg": 256,
                                    "iron_mg": 1,
                                    "vitamin_c_mg": 0,
                                },
                            },
                        },
                        {
                            "label": "rice",
                            "confidence": "medium",
                            "estimated_portion_description": "100 g",
                            "estimated_amount": 100,
                            "estimated_unit": "g",
                            "portion_confidence": "medium",
                            "item_count": 1,
                            "item_count_confidence": "medium",
                            "usda_match": {
                                "fdc_id": 54321,
                                "description": "Rice, cooked",
                                "data_type": "Foundation",
                                "brand_owner": None,
                                "serving_size": 100,
                                "serving_size_unit": "g",
                                "household_serving_fulltext": "1 serving",
                                "source": "USDA FoodData Central",
                                "nutrients": {
                                    "calories": 130,
                                    "protein_g": 2.7,
                                    "carbs_g": 28.2,
                                    "fat_g": 0.3,
                                    "fiber_g": 0.4,
                                    "sodium_mg": 5,
                                    "potassium_mg": 35,
                                    "iron_mg": 0.2,
                                    "vitamin_c_mg": 0,
                                },
                            },
                        },
                    ],
                    moderation_flags=[],
                    food_relevance="food",
                    safe_to_process=True,
                    requires_user_clarification=False,
                    raw_response={"food_relevance": "food"},
                )

        orchestrator = MealAnalysisOrchestrator(
            InMemoryMealStore(),
            vision_client=USDANutritionVisionClient(),
        )
        record = orchestrator.create_meal(
            "user-1",
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
            ),
        )
        self.assertAlmostEqual(record.analysis.nutrition_summary.totals.calories, 363.88, places=2)
        self.assertAlmostEqual(record.analysis.nutrition_summary.totals.protein_g, 46.6, places=1)
        self.assertEqual(record.analysis.nutrition_summary.matched_item_count, 2)
        self.assertTrue(record.analysis.nutrition_summary.insights)
        joined_insights = " ".join(record.analysis.nutrition_summary.insights)
        self.assertNotIn("USDA nutrition details were attached", joined_insights)
        self.assertNotIn("portion-size scaling", joined_insights)

    def test_orchestrator_multiplies_repeated_discrete_items_by_item_count(self) -> None:
        class TacoVisionClient:
            def analyze_upload(self, upload: UploadRequest) -> VisionInference:
                return VisionInference(
                    image_labels=["food", "meal", "plate"],
                    detected_components=["beef tacos"],
                    meal_items=[
                        {
                            "label": "beef taco",
                            "confidence": "high",
                            "notes": "three tacos visible on the plate",
                            "estimated_portion_description": "about 1 taco each",
                            "estimated_amount": None,
                            "estimated_unit": None,
                            "portion_confidence": "medium",
                            "item_count": 3,
                            "item_count_confidence": "high",
                            "usda_match": {
                                "fdc_id": 777,
                                "description": "Beef taco",
                                "data_type": "Survey",
                                "brand_owner": None,
                                "serving_size": None,
                                "serving_size_unit": None,
                                "household_serving_fulltext": "1 taco",
                                "source": "USDA FoodData Central",
                                "nutrients": {
                                    "calories": 210,
                                    "protein_g": 11,
                                    "carbs_g": 18,
                                    "fat_g": 10,
                                    "fiber_g": 2,
                                    "sodium_mg": 320,
                                    "potassium_mg": 180,
                                    "iron_mg": 1.4,
                                    "vitamin_c_mg": 1,
                                },
                            },
                        }
                    ],
                    moderation_flags=[],
                    food_relevance="food",
                    safe_to_process=True,
                    requires_user_clarification=False,
                    raw_response={"food_relevance": "food"},
                )

        orchestrator = MealAnalysisOrchestrator(
            InMemoryMealStore(),
            vision_client=TacoVisionClient(),
        )
        record = orchestrator.create_meal(
            "user-1",
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
            ),
        )
        self.assertAlmostEqual(record.analysis.nutrition_summary.totals.calories, 630.0, places=1)
        self.assertAlmostEqual(record.analysis.nutrition_summary.totals.protein_g, 33.0, places=1)
        self.assertEqual(record.analysis.meal_items[0].item_count, 3)

    def test_orchestrator_answers_question_with_vision_client(self) -> None:
        orchestrator = MealAnalysisOrchestrator(
            InMemoryMealStore(),
            vision_client=FakeVisionClient(),
        )
        record = orchestrator.create_meal(
            "user-1",
            UploadRequest(
                filename="meal.jpg",
                mime_type="image/jpeg",
                size_bytes=1000,
                image_base64="ZmFrZQ==",
            ),
        )
        answer = orchestrator.answer_meal_question(record.meal_id, "Which item has the most protein?")
        self.assertIn("grilled chicken", answer["answer"].lower())
        self.assertIn("not medical advice", answer["answer"].lower())

    def test_orchestrator_fallback_answer_uses_summary(self) -> None:
        orchestrator = MealAnalysisOrchestrator(InMemoryMealStore(), vision_client=None)
        record = orchestrator.store.create(
            MealRecord(
                meal_id=orchestrator.store.next_id(),
                user_id="user-1",
                status="completed",
                validation=ValidationResult(
                    status="accepted",
                    reason_code="accepted",
                    safe_to_process=True,
                    food_relevance="food",
                    moderation_flags=[],
                ),
                analysis={
                    "nutrition_summary": {
                        "totals": {
                            "calories": 420,
                            "protein_g": 35,
                            "carbs_g": 28,
                            "fat_g": 12,
                        }
                    }
                },
            )
        )
        answer = orchestrator.answer_meal_question(record.meal_id, "How much protein is in this meal?")
        self.assertIn("35", answer["answer"])
        self.assertIn("not medical advice", answer["answer"].lower())


if __name__ == "__main__":
    unittest.main()
