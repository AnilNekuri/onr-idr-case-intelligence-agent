"""Deterministic tests for conversational intake routing."""

import pytest

from app.models import (
    DisputeDocumentExtraction,
    DisputeDocumentType,
    ExtractedDisputeDocument,
    ExtractionSource,
)
from app.services.assistant_routing import (
    AssistantRoute,
    build_extraction_message,
    route_assistant_message,
)


@pytest.mark.parametrize(
    "message",
    [
        "I want to process a claim",
        "Can you help me upload my dispute?",
        "Start an IDR case",
        "I have a claim",
    ],
)
def test_claim_processing_language_routes_to_pdf_intake(message: str) -> None:
    assert route_assistant_message(message) is AssistantRoute.CLAIM_INTAKE


@pytest.mark.parametrize(
    "message",
    [
        "What is IDR?",
        "How long is open negotiation?",
        "What information belongs in an ONR notice?",
    ],
)
def test_general_questions_route_to_rag(message: str) -> None:
    assert route_assistant_message(message) is AssistantRoute.GENERAL_QUESTION


def test_unknown_document_stops_the_workflow() -> None:
    result = _result(DisputeDocumentType.UNKNOWN)

    message = build_extraction_message(result)

    assert "can't continue" in message
    assert "ONR or IDR" in message


def test_onr_document_selects_onr_workflow_and_lists_missing_fields() -> None:
    result = _result(DisputeDocumentType.ONR, ["claim_number", "provider_npi"])

    message = build_extraction_message(result)

    assert "**ONR**" in message
    assert "claim number" in message
    assert "open-negotiation workflow" in message


def test_idr_document_selects_idr_workflow() -> None:
    message = build_extraction_message(_result(DisputeDocumentType.IDR))

    assert "**IDR**" in message
    assert "Federal IDR workflow" in message


def _result(
    document_type: DisputeDocumentType,
    missing_fields: list[str] | None = None,
) -> DisputeDocumentExtraction:
    return DisputeDocumentExtraction(
        document=ExtractedDisputeDocument(
            document_type=document_type,
            source_file_name="synthetic.pdf",
        ),
        missing_fields=missing_fields or [],
        extraction_mode=ExtractionSource.HYBRID,
    )
