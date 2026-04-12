from __future__ import annotations

import json
import os
import time
from typing import Any

from app_api.models import UploadRequest, VisionInference
from app_api.schemas import (
    InferencePayload,
    ModerationPayload,
    ObserverPayload,
    OutputReviewPayload,
    OutputSafetyReviewPayload,
    QuestionAnswerPayload,
    QuestionSafety,
    TimingBreakdown,
)
from app_api.usda_client import USDAFoodDataClient
from pydantic import ValidationError

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


VISION_LABELS = [
    "food",
    "meal",
    "plate",
    "fruit",
    "vegetable",
    "dish",
    "drink",
    "document",
    "screenshot",
    "landscape",
    "pet",
    "person_only",
    "meme",
    "vehicle",
    "explicit_nudity",
    "sexual_content",
    "graphic_violence",
    "self_harm",
    "hate_symbol",
]

MODERATION_CATEGORY_MAP = {
    "sexual": "sexual_content",
    "sexual/minors": "sexual_content",
    "violence/graphic": "graphic_violence",
    "self-harm": "self_harm",
    "self-harm/intent": "self_harm",
    "self-harm/instructions": "self_harm",
    "hate": "hate_symbol",
    "hate/threatening": "hate_symbol",
}


def _ensure_data_url(mime_type: str, image_base64: str) -> str:
    if image_base64.startswith("data:"):
        return image_base64
    return f"data:{mime_type};base64,{image_base64}"


def _extract_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    if cleaned.startswith("{") or cleaned.startswith("["):
        return cleaned

    object_start = cleaned.find("{")
    object_end = cleaned.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        return cleaned[object_start : object_end + 1]

    array_start = cleaned.find("[")
    array_end = cleaned.rfind("]")
    if array_start != -1 and array_end != -1 and array_end > array_start:
        return cleaned[array_start : array_end + 1]

    return cleaned


class OpenAIResponsesMealAnalyzer:
    def __init__(
        self,
        model: str | None = None,
        client: Any | None = None,
        usda_client: USDAFoodDataClient | None = None,
    ):
        self.model = model or os.environ.get("OPENAI_MEAL_MODEL", "gpt-5-mini")
        self.observer_model = os.environ.get("OPENAI_OBSERVER_MODEL", "gpt-5-nano")
        self.output_review_model = os.environ.get("OPENAI_OUTPUT_REVIEW_MODEL", "gpt-5-nano")
        self.client = client or self._build_client()
        self.usda_client = usda_client or USDAFoodDataClient()

    def _build_client(self) -> Any:
        if OpenAI is None:  # pragma: no cover
            raise RuntimeError("openai package is not installed")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:  # pragma: no cover
            raise RuntimeError("OPENAI_API_KEY is not set")
        return OpenAI(api_key=api_key)

    def analyze_upload(self, upload: UploadRequest) -> VisionInference:
        if not upload.image_base64:
            raise ValueError("image_base64 is required for multimodal analysis")

        pipeline_started_at = time.perf_counter()
        moderation = self._moderate_upload(upload)
        if moderation["flagged"]:
            return VisionInference(
                image_labels=moderation["image_labels"],
                detected_components=[],
                meal_items=[],
                moderation_flags=moderation["flags"],
                food_relevance="non_food",
                safe_to_process=False,
                requires_user_clarification=False,
                raw_response={
                    "moderation": moderation["raw_response"],
                    "observer": None,
                    "model_output": None,
                    "tool_results": [],
                    "timings_ms": {
                        "moderation": moderation["duration_ms"],
                        "observer": None,
                        "inference": None,
                        "total": round((time.perf_counter() - pipeline_started_at) * 1000, 1),
                    },
                    "blocked_before_model": True,
                    "reason": "unsafe_content",
                },
            )

        observer = self._observe_food_relevance(upload)
        observer_relevance = observer["payload"].get("food_relevance", "uncertain")
        observer_labels = observer["payload"].get("image_labels", [])
        if observer_relevance != "food":
            return VisionInference(
                image_labels=observer_labels,
                detected_components=[],
                meal_items=[],
                moderation_flags=[],
                food_relevance=observer_relevance,
                safe_to_process=True,
                requires_user_clarification=observer_relevance == "uncertain",
                raw_response={
                    "moderation": moderation["raw_response"],
                    "observer": observer["raw_response"],
                    "model_output": None,
                    "tool_results": [],
                    "timings_ms": {
                        "moderation": moderation["duration_ms"],
                        "observer": observer["duration_ms"],
                        "inference": None,
                        "total": round((time.perf_counter() - pipeline_started_at) * 1000, 1),
                    },
                    "blocked_before_model": True,
                    "reason": "observer_filtered",
                },
            )

        payload, tool_results, inference_duration_ms = self._infer_meal_items_with_usda(upload)
        meal_output_review = self._review_meal_output_safety(payload)
        return VisionInference(
            image_labels=payload.get("image_labels", []),
            detected_components=payload.get("detected_components", []),
            meal_items=payload.get("meal_items", []),
            moderation_flags=payload.get("moderation_flags", []),
            food_relevance=payload.get("food_relevance", "uncertain"),
            safe_to_process=bool(payload.get("safe_to_process", False)),
            requires_user_clarification=bool(payload.get("requires_user_clarification", False)),
            raw_response={
                "moderation": moderation["raw_response"],
                "observer": observer["raw_response"],
                "model_output": payload,
                "output_review": meal_output_review["raw_response"],
                "tool_results": tool_results,
                "timings_ms": {
                    "moderation": moderation["duration_ms"],
                    "observer": observer["duration_ms"],
                    "inference": inference_duration_ms,
                    "output_review": meal_output_review["duration_ms"],
                    "total": round((time.perf_counter() - pipeline_started_at) * 1000, 1),
                },
            },
        )

    def answer_question(self, meal_record: Any, question: str) -> dict[str, Any]:
        analysis = meal_record.analysis.model_dump() if getattr(meal_record, "analysis", None) is not None else {}
        question_started_at = time.perf_counter()
        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "You are answering follow-up questions about a meal analysis for a general wellness app. "
                "Use only the provided meal analysis context. "
                "Do not provide medical advice, diagnosis, treatment guidance, medication advice, or disease claims. "
                "If the user asks for medical interpretation, gently refuse that part and stay within general nutrition information. "
                "Keep the answer concise and practical, and end with a short reminder that this is not medical advice."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Meal analysis context:\n"
                                + json.dumps(analysis, indent=2)
                                + "\n\nUser question:\n"
                                + question
                            ),
                        }
                    ],
                }
            ],
        )
        answer = (getattr(response, "output_text", "") or "").strip()
        if not answer:
            raise RuntimeError("Question answering returned no output text")
        answer_generation_ms = round((time.perf_counter() - question_started_at) * 1000, 1)
        review_started_at = time.perf_counter()
        answer = self._review_output_safety(question, analysis, answer)
        review_ms = round((time.perf_counter() - review_started_at) * 1000, 1)
        disclaimer = meal_record.disclaimer
        if disclaimer.lower() not in answer.lower():
            answer = answer.rstrip() + f"\n\nDisclaimer: {disclaimer}"
        return self._validate_schema(
            QuestionAnswerPayload,
            {
                "question": question,
                "answer": answer,
                "disclaimer": disclaimer,
                "safety": {
                    "is_safe": True,
                    "medical_language_blocked": False,
                    "notes": "Reviewed and constrained to general wellness language.",
                },
                "timings_ms": {
                    "answer_generation": answer_generation_ms,
                    "output_review": review_ms,
                    "total": round((time.perf_counter() - question_started_at) * 1000, 1),
                },
            },
            "question answer payload",
        )

    def _moderate_upload(self, upload: UploadRequest) -> dict[str, Any]:
        started_at = time.perf_counter()
        moderation_response = self.client.moderations.create(
            model="omni-moderation-latest",
            input=[
                {"type": "text", "text": upload.text or ""},
                {
                    "type": "image_url",
                    "image_url": {"url": _ensure_data_url(upload.mime_type, upload.image_base64 or "")},
                },
            ],
        )
        result = moderation_response.results[0]
        categories = self._to_plain_dict(getattr(result, "categories", {}))
        flagged_categories = sorted(
            {
                MODERATION_CATEGORY_MAP[key]
                for key, value in categories.items()
                if value and key in MODERATION_CATEGORY_MAP
            }
        )
        validated = self._validate_schema(
            ModerationPayload,
            {
                "flagged": bool(getattr(result, "flagged", False)),
                "categories": flagged_categories,
                "image_labels": flagged_categories,
                "reason": "unsafe image or text" if flagged_categories else None,
                "requires_user_clarification": False,
            },
            "moderation stage",
        )
        return {
            "flagged": validated["flagged"],
            "flags": validated["categories"],
            "image_labels": validated["image_labels"],
            "raw_response": self._to_plain_dict(moderation_response),
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
        }

    def _observe_food_relevance(self, upload: UploadRequest) -> dict[str, Any]:
        started_at = time.perf_counter()
        response = self.client.responses.create(
            model=self.observer_model,
            text={"format": self._observer_response_format()},
            instructions=(
                "You are a low-cost observer for a meal analyzer app. "
                "Decide whether the image is food, non_food, or uncertain before detailed inference. "
                "Return JSON with keys: food_relevance, image_labels, requires_user_clarification, observer_notes. "
                "food_relevance must be one of food, non_food, uncertain. "
                "image_labels must use only these labels when applicable: "
                + ", ".join(VISION_LABELS)
                + ". "
                "If it is clearly not food, prefer labels like document, screenshot, landscape, pet, person_only, meme, or vehicle. "
                "If it is clearly food, include labels like food, meal, plate, fruit, vegetable, dish, or drink."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Classify whether this image is a food image before detailed meal analysis. "
                                "User text: " + (upload.text if upload.text else "No additional text provided.")
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": _ensure_data_url(upload.mime_type, upload.image_base64),
                        },
                    ],
                }
            ],
        )
        text = getattr(response, "output_text", "") or ""
        if not text:
            raise RuntimeError("Observer model returned no output text")
        payload = self._validate_schema(
            ObserverPayload,
            self._parse_json_payload(text, "observer model"),
            "observer model",
        )
        return {
            "payload": payload,
            "raw_response": payload,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
        }

    def _infer_meal_items_with_usda(self, upload: UploadRequest) -> tuple[dict[str, Any], list[dict[str, Any]], float]:
        started_at = time.perf_counter()
        response = self.client.responses.create(
            model=self.model,
            text={"format": self._meal_inference_response_format()},
            instructions=(
                "You are a meal-image analyzer for a general wellness app. "
                "You must not provide medical advice. "
                "First identify the visible food items in the image. "
                "Before you do any USDA matching, perform a dedicated visual counting pass for repeated discrete foods on the plate. "
                "This counting pass is required for foods such as tacos, sushi rolls or pieces, dumplings, wings, sliders, cookies, meatballs, or slices. "
                "Explicitly count repeated discrete items when possible, such as tacos, sushi pieces, wings, cookies, or slices. "
                "If there are multiple identical items, return one meal_item with item_count set to the number of visible items. "
                "Do not collapse three tacos into one taco. "
                "Do not default item_count to 1 if multiple matching items are visibly present. "
                "If there are clearly multiple items but exact counting is somewhat uncertain, still provide your best estimate in item_count and lower item_count_confidence. "
                "Use notes to mention when some items are partially occluded or difficult to count. "
                "When both count and portion are present, item_count should represent the number of repeated items and "
                "estimated_portion_description / estimated_amount should describe one item unless the image clearly suggests a total shared portion instead. "
                "For repeated foods, prefer labels like 'beef taco' with item_count 3 over a single generic label like 'tacos' without a count. "
                "Estimate portion sizes when possible using approximate household or weight-based descriptions. "
                "Then use the available USDA tools to search for matching foods and fetch nutrition details. "
                "For each visible food item, call search_usda_foods, choose the best likely USDA match, "
                "then call get_usda_food_details for that match when possible. "
                "Return JSON with keys: image_labels, moderation_flags, food_relevance, safe_to_process, "
                "requires_user_clarification, detected_components, meal_items. "
                "food_relevance must be one of food, non_food, uncertain. "
                "detected_components should be a short list of visible foods. "
                "meal_items should be objects with keys label, confidence, notes, estimated_portion_description, "
                "estimated_amount, estimated_unit, portion_confidence, item_count, item_count_confidence, and optional usda_match. "
                "When usda_match is present, it must be an object containing fdc_id, description, data_type, "
                "brand_owner, serving_size, serving_size_unit, household_serving_fulltext, source, and nutrients."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Inspect this meal image, identify the visible food items, and attach USDA nutrition info "
                                "for the best matching foods. User text: "
                                + (upload.text if upload.text else "No additional text provided.")
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": _ensure_data_url(upload.mime_type, upload.image_base64),
                        },
                    ],
                }
            ],
            tools=self._build_tools(),
            parallel_tool_calls=True,
        )

        tool_results: list[dict[str, Any]] = []
        while True:
            function_calls = [item for item in getattr(response, "output", []) if getattr(item, "type", "") == "function_call"]
            if not function_calls:
                break

            tool_outputs = []
            for call in function_calls:
                result = self._run_tool(call.name, json.loads(call.arguments))
                tool_results.append(
                    {
                        "name": call.name,
                        "arguments": json.loads(call.arguments),
                        "output": result,
                    }
                )
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result),
                    }
                )

            response = self.client.responses.create(
                model=self.model,
                previous_response_id=response.id,
                text={"format": self._meal_inference_response_format()},
                input=tool_outputs,
                tools=self._build_tools(),
                parallel_tool_calls=True,
            )

        text = getattr(response, "output_text", "") or ""
        if not text:
            raise RuntimeError("Responses API returned no output text")
        payload = self._validate_schema(
            InferencePayload,
            self._parse_json_payload(text, "meal inference model"),
            "meal inference model",
        )
        return (
            payload,
            tool_results,
            round((time.perf_counter() - started_at) * 1000, 1),
        )

    def _build_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "search_usda_foods",
                "description": "Search USDA FoodData Central for foods matching a visible meal item.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A short food search query like grilled chicken, white rice, or broccoli.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of USDA candidate foods to return.",
                        },
                    },
                    "required": ["query", "limit"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_usda_food_details",
                "description": "Fetch detailed USDA FoodData Central nutrition for a specific FDC food id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fdc_id": {
                            "type": "integer",
                            "description": "The USDA FoodData Central FDC id for the selected food.",
                        }
                    },
                    "required": ["fdc_id"],
                    "additionalProperties": False,
                },
            },
        ]

    def _output_review_response_format(self) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": "output_safety_review_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "is_safe": {"type": "boolean"},
                    "answer": {"type": "string"},
                },
                "required": ["is_safe", "answer"],
                "additionalProperties": False,
            },
        }

    def _meal_output_review_response_format(self) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": "meal_output_review_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "is_safe": {"type": "boolean"},
                    "notes": {"type": "string"},
                },
                "required": ["is_safe", "notes"],
                "additionalProperties": False,
            },
        }

    def _review_meal_output_safety(self, payload: dict[str, Any]) -> dict[str, Any]:
        started_at = time.perf_counter()
        response = self.client.responses.create(
            model=self.output_review_model,
            text={"format": self._meal_output_review_response_format()},
            instructions=(
                "You are a low-cost output safety reviewer for a nutrition app. "
                "Review the structured meal analysis output and decide whether it is safe to show as general wellness information. "
                "Reject medical framing, diagnosis, treatment guidance, medication advice, or disease-management advice. "
                "Return whether the structured output is safe to display and a short note."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Structured meal analysis output:\n" + json.dumps(payload, indent=2),
                        }
                    ],
                }
            ],
        )
        text = (getattr(response, "output_text", "") or "").strip()
        if not text:
            raise RuntimeError("Meal output safety reviewer returned no output text")
        return {
            "raw_response": self._validate_schema(
                OutputReviewPayload,
                self._parse_json_payload(text, "meal output safety reviewer"),
                "meal output safety reviewer",
            ),
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
        }

    def _review_output_safety(self, question: str, analysis: dict[str, Any], draft_answer: str) -> str:
        response = self.client.responses.create(
            model=self.output_review_model,
            text={"format": self._output_review_response_format()},
            instructions=(
                "You are a low-cost output safety reviewer for a nutrition app. "
                "Rewrite the draft answer so it stays general, non-medical, and free of diagnosis, treatment, medication, "
                "or disease-management advice. Preserve useful nutrition information from the provided meal analysis context. "
                "If the question asks for medical advice, softly refuse that part and keep the answer within general wellness information."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Meal analysis context:\n"
                                + json.dumps(analysis, indent=2)
                                + "\n\nUser question:\n"
                                + question
                                + "\n\nDraft answer:\n"
                                + draft_answer
                            ),
                        }
                    ],
                }
            ],
        )
        text = (getattr(response, "output_text", "") or "").strip()
        if not text:
            raise RuntimeError("Output safety reviewer returned no output text")
        payload = self._validate_schema(
            OutputSafetyReviewPayload,
            self._parse_json_payload(text, "output safety reviewer"),
            "output safety reviewer",
        )
        return payload.get("answer", draft_answer).strip() or draft_answer

    def _observer_response_format(self) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": "meal_observer_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "food_relevance": {
                        "type": "string",
                        "enum": ["food", "non_food", "uncertain"],
                    },
                    "image_labels": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "requires_user_clarification": {"type": "boolean"},
                    "observer_notes": {"type": "string"},
                },
                "required": [
                    "food_relevance",
                    "image_labels",
                    "requires_user_clarification",
                    "observer_notes",
                ],
                "additionalProperties": False,
            },
        }

    def _meal_inference_response_format(self) -> dict[str, Any]:
        usda_match_schema = {
            "type": "object",
            "properties": {
                "fdc_id": {"type": "integer"},
                "description": {"type": "string"},
                "data_type": {"type": ["string", "null"]},
                "brand_owner": {"type": ["string", "null"]},
                "serving_size": {"type": ["number", "null"]},
                "serving_size_unit": {"type": ["string", "null"]},
                "household_serving_fulltext": {"type": ["string", "null"]},
                "source": {"type": "string"},
                "nutrients": {
                    "type": "object",
                    "properties": {
                        "calories": {"type": ["number", "null"]},
                        "protein_g": {"type": ["number", "null"]},
                        "carbs_g": {"type": ["number", "null"]},
                        "fat_g": {"type": ["number", "null"]},
                        "fiber_g": {"type": ["number", "null"]},
                        "sodium_mg": {"type": ["number", "null"]},
                        "potassium_mg": {"type": ["number", "null"]},
                        "iron_mg": {"type": ["number", "null"]},
                        "vitamin_c_mg": {"type": ["number", "null"]},
                    },
                    "required": [
                        "calories",
                        "protein_g",
                        "carbs_g",
                        "fat_g",
                        "fiber_g",
                        "sodium_mg",
                        "potassium_mg",
                        "iron_mg",
                        "vitamin_c_mg",
                    ],
                    "additionalProperties": False,
                },
            },
            "required": [
                "fdc_id",
                "description",
                "data_type",
                "brand_owner",
                "serving_size",
                "serving_size_unit",
                "household_serving_fulltext",
                "source",
                "nutrients",
            ],
            "additionalProperties": False,
        }
        return {
            "type": "json_schema",
            "name": "meal_inference_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "image_labels": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "moderation_flags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "food_relevance": {
                        "type": "string",
                        "enum": ["food", "non_food", "uncertain"],
                    },
                    "safe_to_process": {"type": "boolean"},
                    "requires_user_clarification": {"type": "boolean"},
                    "detected_components": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "meal_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "confidence": {"type": "string"},
                                "notes": {"type": ["string", "null"]},
                                "estimated_portion_description": {"type": ["string", "null"]},
                                "estimated_amount": {"type": ["number", "null"]},
                                "estimated_unit": {"type": ["string", "null"]},
                                "portion_confidence": {"type": ["string", "null"]},
                                "item_count": {"type": ["integer", "null"]},
                                "item_count_confidence": {"type": ["string", "null"]},
                                "usda_match": {
                                    "anyOf": [
                                        usda_match_schema,
                                        {"type": "null"},
                                    ]
                                },
                            },
                            "required": [
                                "label",
                                "confidence",
                                "notes",
                                "estimated_portion_description",
                                "estimated_amount",
                                "estimated_unit",
                                "portion_confidence",
                                "item_count",
                                "item_count_confidence",
                                "usda_match",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "image_labels",
                    "moderation_flags",
                    "food_relevance",
                    "safe_to_process",
                    "requires_user_clarification",
                    "detected_components",
                    "meal_items",
                ],
                "additionalProperties": False,
            },
        }

    def _run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "search_usda_foods":
            result = self.usda_client.search_foods(
                query=arguments["query"],
                limit=int(arguments["limit"]),
            )
            return result.model_dump() if hasattr(result, "model_dump") else result
        if name == "get_usda_food_details":
            result = self.usda_client.get_food_details(int(arguments["fdc_id"]))
            return result.model_dump() if hasattr(result, "model_dump") else result
        raise RuntimeError(f"Unknown tool call: {name}")

    def _parse_json_payload(self, text: str, stage: str) -> dict[str, Any]:
        candidate = _extract_json_text(text)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as error:
            preview = candidate[:300] if candidate else "<empty>"
            raise RuntimeError(f"{stage} returned invalid JSON: {preview}") from error
        if not isinstance(payload, dict):
            raise RuntimeError(f"{stage} returned JSON that was not an object")
        return payload

    def _validate_schema(self, schema: Any, payload: dict[str, Any], stage: str) -> dict[str, Any]:
        try:
            validated = schema.model_validate(payload)
        except ValidationError as error:
            raise RuntimeError(f"{stage} did not match schema: {error}") from error
        return validated.model_dump()

    def _to_plain_dict(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, dict):
            return {key: self._to_plain_dict(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_plain_dict(item) for item in value]
        if hasattr(value, "__dict__"):
            return {
                key: self._to_plain_dict(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        return value
