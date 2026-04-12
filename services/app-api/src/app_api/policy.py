from __future__ import annotations

import re

from app_api.models import UploadRequest, ValidationResult


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/heic"}
UNSAFE_TERMS = {
    "sexual": ["nude", "explicit", "porn", "sex", "nsfw"],
    "self_harm": ["self-harm", "suicide", "cutting"],
    "hate": ["slur", "kill them"],
    "medical": ["diagnose", "medication", "insulin dose", "treatment plan"],
    "eating_disorder": ["starve", "purge", "extreme weight loss"],
}
NON_FOOD_LABELS = {
    "document",
    "screenshot",
    "landscape",
    "pet",
    "person_only",
    "meme",
    "vehicle",
}
UNSAFE_IMAGE_LABELS = {
    "explicit_nudity",
    "sexual_content",
    "graphic_violence",
    "self_harm",
    "hate_symbol",
}
FOOD_LABELS = {"food", "meal", "plate", "fruit", "vegetable", "dish", "drink"}


def _extract_flags(text: str) -> list[str]:
    flags: list[str] = []
    normalized = text.lower()
    for label, terms in UNSAFE_TERMS.items():
        for term in terms:
            if re.search(r"\b" + re.escape(term) + r"\b", normalized):
                flags.append(label)
                break
    return flags


def validate_upload(upload: UploadRequest) -> ValidationResult:
    moderation_flags = _extract_flags(upload.text)
    image_flags = [label for label in upload.image_labels if label in UNSAFE_IMAGE_LABELS]
    moderation_flags.extend(image_flags)

    if upload.mime_type not in ALLOWED_MIME_TYPES:
        return ValidationResult(
            status="rejected",
            reason_code="unsupported_file_type",
            safe_to_process=False,
            food_relevance="non_food",
            moderation_flags=moderation_flags,
        )
    if upload.size_bytes > MAX_UPLOAD_BYTES:
        return ValidationResult(
            status="rejected",
            reason_code="file_too_large",
            safe_to_process=False,
            food_relevance="non_food",
            moderation_flags=moderation_flags,
        )
    if moderation_flags:
        return ValidationResult(
            status="rejected",
            reason_code="unsafe_content",
            safe_to_process=False,
            food_relevance="non_food",
            moderation_flags=moderation_flags,
        )

    labels = set(upload.image_labels)
    if labels & NON_FOOD_LABELS and not labels & FOOD_LABELS:
        return ValidationResult(
            status="rejected",
            reason_code="non_food_image",
            safe_to_process=False,
            food_relevance="non_food",
            moderation_flags=[],
        )
    if labels & FOOD_LABELS:
        return ValidationResult(
            status="accepted",
            reason_code="accepted",
            safe_to_process=True,
            food_relevance="food",
            moderation_flags=[],
        )
    return ValidationResult(
        status="needs_clarification",
        reason_code="uncertain_food_image",
        safe_to_process=True,
        food_relevance="uncertain",
        moderation_flags=[],
    )


def guard_output_insights(insights: list[str]) -> list[str]:
    blocked_patterns = [
        "diagnose",
        "treat",
        "cure",
        "prevent disease",
        "medication",
        "insulin",
        "prescription",
    ]
    filtered = []
    for insight in insights:
        lowered = insight.lower()
        if any(pattern in lowered for pattern in blocked_patterns):
            continue
        filtered.append(insight)
    if not filtered:
        filtered.append("Nutrition estimates are limited to general wellness observations.")
    return filtered
