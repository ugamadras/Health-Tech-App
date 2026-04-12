from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app_api.schemas import MealAnalysisPayload, MealItem


DISCLAIMER = (
    "These meal-item detections are for general informational purposes only. "
    "They are not medical advice. All values are estimates, and actual quantities may vary."
)


class AppModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UploadRequest(AppModel):
    filename: str
    mime_type: str
    size_bytes: int
    text: str = ""
    image_base64: Optional[str] = None
    image_labels: list[str] = Field(default_factory=list)
    meal_items: list[dict[str, Any]] = Field(default_factory=list)


class ValidationResult(AppModel):
    status: str
    reason_code: str
    safe_to_process: bool
    food_relevance: str
    moderation_flags: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class MealRecord(AppModel):
    meal_id: str
    user_id: str
    status: str
    validation: ValidationResult
    analysis: Optional[MealAnalysisPayload] = None
    detected_components: list[str] = Field(default_factory=list)
    model_response: Optional[dict[str, Any]] = None
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class VisionInference(AppModel):
    image_labels: list[str] = Field(default_factory=list)
    detected_components: list[str] = Field(default_factory=list)
    meal_items: list[MealItem] = Field(default_factory=list)
    moderation_flags: list[str] = Field(default_factory=list)
    food_relevance: str
    safe_to_process: bool
    requires_user_clarification: bool
    raw_response: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
