"""Unit tests for the case domain models."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.models import Case, CaseEventType, CaseStatus, CaseType


def valid_case_data() -> dict[str, object]:
    """Return a complete synthetic case matching the project guide."""
    return {
        "case_id": "CASE-1001",
        "case_type": "ONR",
        "status": "PENDING_PROVIDER_RESPONSE",
        "created_date": "2026-08-01",
        "open_negotiation_start_date": "2026-08-02",
        "open_negotiation_end_date": "2026-08-31",
        "provider_name": "Synthetic Provider A",
        "provider_response_received": False,
        "missing_documents": [],
        "documents": [
            {
                "document_id": "DOC-001",
                "file_name": "negotiation_notice.pdf",
                "s3_key": "CASE-1001/negotiation_notice.pdf",
            }
        ],
        "events": [
            {
                "date": "2026-08-01",
                "type": "CASE_CREATED",
                "description": "ONR case created",
            },
            {
                "date": "2026-08-02",
                "type": "NOTICE_SENT",
                "description": "Open negotiation notice sent",
            },
        ],
    }


def test_valid_case() -> None:
    case = Case.model_validate(valid_case_data())

    assert case.case_id == "CASE-1001"
    assert case.case_type is CaseType.ONR
    assert case.status is CaseStatus.PENDING_PROVIDER_RESPONSE
    assert case.created_date == date(2026, 8, 1)
    assert case.documents[0].document_id == "DOC-001"
    assert case.events[0].type is CaseEventType.CASE_CREATED


def test_missing_required_field_is_rejected() -> None:
    case_data = valid_case_data()
    del case_data["provider_name"]

    with pytest.raises(ValidationError, match="provider_name"):
        Case.model_validate(case_data)


def test_invalid_calendar_date_is_rejected() -> None:
    case_data = valid_case_data()
    case_data["created_date"] = "2026-02-30"

    with pytest.raises(ValidationError, match="created_date"):
        Case.model_validate(case_data)


def test_negotiation_end_before_start_is_rejected() -> None:
    case_data = valid_case_data()
    case_data["open_negotiation_end_date"] = "2026-08-01"

    with pytest.raises(
        ValidationError,
        match="open_negotiation_end_date must be on or after",
    ):
        Case.model_validate(case_data)


def test_invalid_case_type_is_rejected() -> None:
    case_data = valid_case_data()
    case_data["case_type"] = "APPEAL"

    with pytest.raises(ValidationError, match="case_type"):
        Case.model_validate(case_data)


def test_case_json_round_trip() -> None:
    case = Case.model_validate(valid_case_data())

    serialized = case.model_dump_json()
    loaded = Case.model_validate_json(serialized)

    assert '"created_date":"2026-08-01"' in serialized
    assert loaded == case
