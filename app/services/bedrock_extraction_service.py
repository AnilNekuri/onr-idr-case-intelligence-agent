"""Semantic ONR/IDR field extraction through Amazon Bedrock."""

import json
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)
from pydantic import ValidationError

from app.models.document_extraction import (
    ExtractedDisputeDocument,
    TextractKeyValue,
)
from app.prompts.dispute_document_extraction_prompt import (
    SYSTEM_PROMPT,
    build_extraction_prompt,
    extraction_json_schema,
    serialized_extraction_json_schema,
)


class BedrockExtractionError(RuntimeError):
    """Raised when Bedrock cannot return a usable extraction."""


class ExtractionValidationError(ValueError):
    """Raised when model output violates the canonical extraction schema."""


class DisputeFieldExtractor(Protocol):
    """Provider-independent semantic extraction contract."""

    def extract_dispute_fields(
        self,
        *,
        file_name: str,
        textract_text: str,
        key_values: list[TextractKeyValue],
    ) -> ExtractedDisputeDocument:
        """Return one validated document from normalized OCR evidence."""
        ...


class BedrockExtractionService:
    """Extract a strict canonical object from normalized Textract evidence."""

    def __init__(
        self,
        model_id: str,
        *,
        region_name: str | None = None,
        profile_name: str | None = None,
        bedrock_runtime_client: Any | None = None,
        max_tokens: int = 2048,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        if bedrock_runtime_client is None:
            session = boto3.Session(
                profile_name=profile_name,
                region_name=region_name,
            )
            bedrock_runtime_client = session.client("bedrock-runtime")
        self._client = bedrock_runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens

    def extract_dispute_fields(
        self,
        *,
        file_name: str,
        textract_text: str,
        key_values: list[TextractKeyValue],
    ) -> ExtractedDisputeDocument:
        """Use constrained JSON generation and validate the result with Pydantic."""
        if not textract_text.strip() and not key_values:
            raise BedrockExtractionError("Textract returned no document content")

        key_values_json = json.dumps(
            [pair.model_dump(mode="json") for pair in key_values],
            separators=(",", ":"),
        )
        prompt = build_extraction_prompt(
            file_name=file_name,
            textract_text=textract_text,
            key_values_json=key_values_json,
        )
        try:
            response = self._client.converse(
                modelId=self._model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": self._max_tokens, "temperature": 0.0},
                outputConfig={
                    "textFormat": {
                        "type": "json_schema",
                        "structure": {
                            "jsonSchema": {
                                "schema": serialized_extraction_json_schema(),
                                "name": "dispute_document_extraction",
                                "description": (
                                    "Uniform fields extracted from an ONR or IDR PDF"
                                ),
                            }
                        },
                    }
                },
            )
            content = response["output"]["message"]["content"]
        except (BotoCoreError, ClientError) as error:
            raise BedrockExtractionError("Amazon Bedrock extraction failed") from error
        except (KeyError, TypeError) as error:
            raise BedrockExtractionError(
                "Amazon Bedrock returned an invalid response structure"
            ) from error

        text = "".join(
            str(block["text"])
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ).strip()
        if not text:
            raise BedrockExtractionError("Amazon Bedrock returned no extraction JSON")

        return validate_extraction_response(text=text, file_name=file_name)


def validate_extraction_response(
    *, text: str, file_name: str
) -> ExtractedDisputeDocument:
    """Parse and validate one provider response against the canonical model."""
    try:
        data = json.loads(_strip_json_fence(text))
        if not isinstance(data, dict):
            raise TypeError("top-level response is not an object")
        properties = extraction_json_schema()["properties"]
        if not isinstance(properties, dict):
            raise TypeError("extraction schema properties are invalid")
        missing = set(properties) - set(data)
        if missing:
            raise ValueError(
                "model response omitted required fields: "
                + ", ".join(sorted(missing))
            )
        data["source_file_name"] = file_name
        return ExtractedDisputeDocument.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as error:
        raise ExtractionValidationError(
            "Amazon Bedrock returned data outside the extraction schema"
        ) from error


def _strip_json_fence(value: str) -> str:
    """Tolerate code fences from models that ignore JSON-only prompting."""
    if not value.startswith("```"):
        return value
    lines = value.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
