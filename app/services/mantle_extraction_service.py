"""Prompt-constrained ONR/IDR extraction through Bedrock Mantle."""

import json

from app.language_models import LanguageModel, LanguageModelError
from app.models.document_extraction import (
    ExtractedDisputeDocument,
    TextractKeyValue,
)
from app.prompts.dispute_document_extraction_prompt import (
    build_mantle_extraction_prompt,
)
from app.services.bedrock_extraction_service import (
    BedrockExtractionError,
    ExtractionValidationError,
    validate_extraction_response,
)


class MantleExtractionService:
    """Generate JSON through Mantle, validate it, and retry invalid responses."""

    def __init__(self, language_model: LanguageModel, *, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._language_model = language_model
        self._max_attempts = max_attempts

    def extract_dispute_fields(
        self,
        *,
        file_name: str,
        textract_text: str,
        key_values: list[TextractKeyValue],
    ) -> ExtractedDisputeDocument:
        """Return validated JSON, retrying when unconstrained output is malformed."""
        if not textract_text.strip() and not key_values:
            raise BedrockExtractionError("Textract returned no document content")

        key_values_json = json.dumps(
            [pair.model_dump(mode="json") for pair in key_values],
            separators=(",", ":"),
        )
        correction: str | None = None
        validation_error: ExtractionValidationError | None = None
        for attempt in range(1, self._max_attempts + 1):
            prompt = build_mantle_extraction_prompt(
                file_name=file_name,
                textract_text=textract_text,
                key_values_json=key_values_json,
                correction=correction,
            )
            try:
                response = self._language_model.generate(prompt)
            except LanguageModelError as error:
                detail = str(error).strip()
                suffix = f": {detail[:500]}" if detail else ""
                raise BedrockExtractionError(
                    f"Amazon Bedrock Mantle extraction failed{suffix}"
                ) from error

            try:
                return validate_extraction_response(
                    text=response,
                    file_name=file_name,
                )
            except ExtractionValidationError as error:
                validation_error = error
                correction = (
                    f"Attempt {attempt} did not match the schema. Return every "
                    "required property, use null for absent scalar values, use [] "
                    "for absent CPT/HCPCS codes, and output JSON only."
                )

        raise ExtractionValidationError(
            f"Amazon Bedrock Mantle returned invalid extraction JSON after "
            f"{self._max_attempts} attempts"
        ) from validation_error
