"""Tests for prompt-constrained extraction through Bedrock Mantle."""

import json
from pathlib import Path

import pytest

from app.language_models import LanguageModelError
from app.services import ExtractionValidationError, MantleExtractionService


class StubLanguageModel:
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


class FailingLanguageModel:
    def generate(self, prompt: str) -> str:
        raise LanguageModelError("synthetic Mantle failure")


def fixture(name: str) -> str:
    return Path("tests/fixtures", name).read_text(encoding="utf-8")


def test_valid_mantle_json_is_validated_on_first_attempt() -> None:
    model = StubLanguageModel(fixture("onr_bedrock_response.json"))
    service = MantleExtractionService(model)

    document = service.extract_dispute_fields(
        file_name="synthetic_onr_case_001.pdf",
        textract_text="Open Negotiation Notice",
        key_values=[],
    )

    assert document.document_type.value == "ONR"
    assert len(model.prompts) == 1
    assert "TARGET JSON SCHEMA" in model.prompts[0]
    assert '"additionalProperties":false' in model.prompts[0]
    assert "Do not use Markdown code fences" in model.prompts[0]


def test_invalid_output_is_retried_with_correction() -> None:
    model = StubLanguageModel(
        "not json",
        json.dumps({"document_type": "ONR"}),
        fixture("onr_bedrock_response.json"),
    )
    service = MantleExtractionService(model, max_attempts=3)

    document = service.extract_dispute_fields(
        file_name="synthetic.pdf",
        textract_text="Open Negotiation Notice",
        key_values=[],
    )

    assert document.document_type.value == "ONR"
    assert len(model.prompts) == 3
    assert "CORRECTION FOR THIS ATTEMPT" in model.prompts[1]
    assert "Attempt 2 did not match the schema" in model.prompts[2]


def test_repeated_invalid_output_fails_safely() -> None:
    model = StubLanguageModel("not json", "still not json")
    service = MantleExtractionService(model, max_attempts=2)

    with pytest.raises(ExtractionValidationError, match="after 2 attempts"):
        service.extract_dispute_fields(
            file_name="synthetic.pdf",
            textract_text="Open Negotiation Notice",
            key_values=[],
        )


def test_mantle_request_failure_includes_safe_provider_detail() -> None:
    service = MantleExtractionService(FailingLanguageModel())

    with pytest.raises(
        RuntimeError,
        match=(
            "Mantle extraction failed: synthetic Mantle failure"
        ),
    ):
        service.extract_dispute_fields(
            file_name="synthetic.pdf",
            textract_text="Open Negotiation Notice",
            key_values=[],
        )
