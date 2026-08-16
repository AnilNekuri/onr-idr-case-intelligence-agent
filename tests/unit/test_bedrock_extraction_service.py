"""Tests for constrained Bedrock extraction and strict validation."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.bedrock_extraction_service import (
    BedrockExtractionService,
    ExtractionValidationError,
)


class FakeBedrockClient:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.request: dict[str, Any] | None = None

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.request = kwargs
        return {
            "output": {
                "message": {"content": [{"text": self.response_text}]}
            }
        }


def test_extracts_and_validates_uniform_json() -> None:
    response = Path("tests/fixtures/idr_bedrock_response.json").read_text(
        encoding="utf-8"
    )
    client = FakeBedrockClient(response)
    service = BedrockExtractionService(
        "synthetic.model-v1", bedrock_runtime_client=client
    )

    document = service.extract_dispute_fields(
        file_name="synthetic_idr_case_001.pdf",
        textract_text="Federal Independent Dispute Resolution",
        key_values=[],
    )

    assert document.document_type.value == "IDR"
    assert document.source_file_name == "synthetic_idr_case_001.pdf"
    assert client.request is not None
    schema = json.loads(
        client.request["outputConfig"]["textFormat"]["structure"]["jsonSchema"][
            "schema"
        ]
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert "untrusted data" in client.request["system"][0]["text"]


def test_rejects_model_output_with_an_unexpected_field() -> None:
    data = json.loads(
        Path("tests/fixtures/onr_bedrock_response.json").read_text(encoding="utf-8")
    )
    data["claim_is_valid"] = True
    service = BedrockExtractionService(
        "synthetic.model-v1",
        bedrock_runtime_client=FakeBedrockClient(json.dumps(data)),
    )

    with pytest.raises(ExtractionValidationError, match="outside the extraction"):
        service.extract_dispute_fields(
            file_name="synthetic.pdf",
            textract_text="Open Negotiation Notice",
            key_values=[],
        )
