from __future__ import annotations

from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


SchemaVersion = Literal["1.0"]
StageName = Literal["moderation", "observer", "inference", "output_review", "qa"]
EnvelopeStatus = Literal["ok", "rejected", "needs_clarification", "error"]
FoodRelevance = Literal["food", "non_food", "uncertain"]
ConfidenceLevel = Literal["low", "medium", "high"]

PayloadT = TypeVar("PayloadT", bound=BaseModel)


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimingBreakdown(SchemaModel):
    moderation: Optional[float] = None
    observer: Optional[float] = None
    inference: Optional[float] = None
    output_review: Optional[float] = None
    answer_generation: Optional[float] = None
    tooling: Optional[float] = None
    total: Optional[float] = None


class USDAFoodNutrients(SchemaModel):
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    vitamin_c_mg: Optional[float] = None


class USDAFoodMatch(SchemaModel):
    fdc_id: int
    description: str
    data_type: str
    brand_owner: Optional[str] = None
    serving_size: Optional[float] = None
    serving_size_unit: Optional[str] = None
    household_serving_fulltext: Optional[str] = None
    source: str = "USDA FoodData Central"
    food_portions: list[dict[str, Any]] = Field(default_factory=list)
    nutrients: USDAFoodNutrients = Field(default_factory=USDAFoodNutrients)


class USDAFoodSearchItem(SchemaModel):
    fdc_id: Optional[int] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    brand_owner: Optional[str] = None


class USDAFoodSearchResponse(SchemaModel):
    query: str
    items: list[USDAFoodSearchItem] = Field(default_factory=list)


class USDAFoodDetailsResponse(SchemaModel):
    fdc_id: Optional[int] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    brand_owner: Optional[str] = None
    serving_size: Optional[float] = None
    serving_size_unit: Optional[str] = None
    household_serving_fulltext: Optional[str] = None
    food_portions: list[dict[str, Any]] = Field(default_factory=list)
    nutrients: USDAFoodNutrients = Field(default_factory=USDAFoodNutrients)
    source: str = "USDA FoodData Central"


class MealItem(SchemaModel):
    label: str
    confidence: ConfidenceLevel = "medium"
    notes: Optional[str] = None
    estimated_portion_description: Optional[str] = None
    estimated_amount: Optional[float] = None
    estimated_unit: Optional[str] = None
    portion_confidence: ConfidenceLevel = "medium"
    item_count: Optional[int] = 1
    item_count_confidence: Optional[ConfidenceLevel] = "medium"
    usda_match: Optional[USDAFoodMatch] = None


class NutritionTotals(SchemaModel):
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0
    potassium_mg: float = 0.0
    iron_mg: float = 0.0
    vitamin_c_mg: float = 0.0


class NutritionSummary(SchemaModel):
    totals: NutritionTotals = Field(default_factory=NutritionTotals)
    matched_item_count: int = 0
    identified_item_count: int = 0
    insights: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "These USDA-based nutrition values are general informational estimates for the identified meal items. "
        "They are not medical advice. All values are estimates, and actual quantities may vary based on preparation, portion size, and ingredients."
    )


class MealAnalysisPayload(SchemaModel):
    detected_components: list[str] = Field(default_factory=list)
    meal_items: list[MealItem] = Field(default_factory=list)
    nutrition_summary: Optional[NutritionSummary] = None


class ModerationPayload(SchemaModel):
    flagged: bool = False
    categories: list[str] = Field(default_factory=list)
    image_labels: list[str] = Field(default_factory=list)
    reason: Optional[str] = None
    requires_user_clarification: bool = False


class ObserverPayload(SchemaModel):
    food_relevance: FoodRelevance
    image_labels: list[str] = Field(default_factory=list)
    requires_user_clarification: bool = False
    observer_notes: str = ""


class InferencePayload(SchemaModel):
    image_labels: list[str] = Field(default_factory=list)
    moderation_flags: list[str] = Field(default_factory=list)
    food_relevance: FoodRelevance = "uncertain"
    safe_to_process: bool = False
    requires_user_clarification: bool = False
    detected_components: list[str] = Field(default_factory=list)
    meal_items: list[MealItem] = Field(default_factory=list)


class OutputReviewPayload(SchemaModel):
    is_safe: bool
    notes: str


class OutputSafetyReviewPayload(SchemaModel):
    is_safe: bool
    answer: str


class QuestionSafety(SchemaModel):
    is_safe: bool = True
    medical_language_blocked: bool = False
    notes: Optional[str] = None


class QuestionAnswerPayload(SchemaModel):
    question: str
    answer: str
    disclaimer: str
    safety: QuestionSafety = Field(default_factory=QuestionSafety)
    timings_ms: TimingBreakdown = Field(default_factory=TimingBreakdown)


class ModelOutputEnvelope(SchemaModel, Generic[PayloadT]):
    schema_version: SchemaVersion = "1.0"
    stage: StageName
    request_id: str
    meal_id: Optional[str] = None
    model: str
    status: EnvelopeStatus = "ok"
    timings_ms: TimingBreakdown = Field(default_factory=TimingBreakdown)
    safety_flags: list[str] = Field(default_factory=list)
    confidence: Optional[ConfidenceLevel] = None
    payload: PayloadT
    raw_response: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ModerationEnvelope(ModelOutputEnvelope[ModerationPayload]):
    stage: Literal["moderation"] = "moderation"
    payload: ModerationPayload


class ObserverEnvelope(ModelOutputEnvelope[ObserverPayload]):
    stage: Literal["observer"] = "observer"
    payload: ObserverPayload


class InferenceEnvelope(ModelOutputEnvelope[InferencePayload]):
    stage: Literal["inference"] = "inference"
    payload: InferencePayload


class OutputReviewEnvelope(ModelOutputEnvelope[OutputReviewPayload]):
    stage: Literal["output_review"] = "output_review"
    payload: OutputReviewPayload


class QuestionAnswerEnvelope(ModelOutputEnvelope[QuestionAnswerPayload]):
    stage: Literal["qa"] = "qa"
    payload: QuestionAnswerPayload


class AuthRequest(SchemaModel):
    email: str
    password: str = ""


class RegisterResponse(SchemaModel):
    user_id: str
    status: str


class LoginResponse(SchemaModel):
    access_token: str
    token_type: str = "bearer"


class MealCreateRequest(SchemaModel):
    filename: str
    mime_type: str
    size_bytes: int
    text: str = ""
    image_base64: Optional[str] = None
    image_labels: list[str] = Field(default_factory=list)
    meal_items: list[dict[str, Any]] = Field(default_factory=list)


class MealListResponse(SchemaModel):
    items: list[Any] = Field(default_factory=list)


class MealQuestionRequest(SchemaModel):
    question: str = ""


class ErrorResponse(SchemaModel):
    error: str


class RootResponse(SchemaModel):
    service: str
    status: str
    docs_url: str
    health_url: str
    web_app_url: str
    openai_responses_enabled: bool
    routes: list[str] = Field(default_factory=list)


class HealthResponse(SchemaModel):
    service: str
    status: str
