"""Expected examples for the local case service."""

from datetime import date
from pathlib import Path

import pytest

from app.models import CaseEvent, CaseEventType, CaseStatus, CaseType, Document
from app.repositories import JsonCaseRepository
from app.services.case_service import CaseAlreadyExistsError, CaseService
from app.tools import DeadlineRisk
from tests.unit.tool_support import make_case


def test_create_case_persists_and_returns_case(tmp_path: Path) -> None:
    file_path = tmp_path / "cases.json"
    service = CaseService(JsonCaseRepository(file_path))
    expected_case = make_case(case_id="CASE-NEW")

    created_case = service.create_case(expected_case)
    reloaded_service = CaseService(JsonCaseRepository(file_path))

    assert created_case is expected_case
    assert reloaded_service.get_case("CASE-NEW") == expected_case


def test_get_case_returns_none_for_unknown_id(tmp_path: Path) -> None:
    service = CaseService(JsonCaseRepository(tmp_path / "cases.json"))

    assert service.get_case("CASE-UNKNOWN") is None


def test_update_case_replaces_existing_case(tmp_path: Path) -> None:
    service = CaseService(JsonCaseRepository(tmp_path / "cases.json"))
    original = make_case(case_id="CASE-UPDATE", status=CaseStatus.NEW)
    updated = original.model_copy(update={"status": CaseStatus.COMPLETE})
    service.create_case(original)

    returned = service.update_case(updated)

    assert returned is updated
    assert service.get_case("CASE-UPDATE") == updated


def test_get_timeline_returns_sorted_events(tmp_path: Path) -> None:
    later_event = CaseEvent(
        date=date(2026, 8, 3),
        type=CaseEventType.NOTICE_SENT,
        description="Notice sent",
    )
    earlier_event = CaseEvent(
        date=date(2026, 8, 1),
        type=CaseEventType.CASE_CREATED,
        description="Case created",
    )
    case = make_case(events=[later_event, earlier_event])
    service = CaseService(JsonCaseRepository(tmp_path / "cases.json"))
    service.create_case(case)

    assert service.get_timeline(case.case_id) == [earlier_event, later_event]


def test_get_missing_information_applies_deterministic_rules(
    tmp_path: Path,
) -> None:
    case = make_case(
        status=CaseStatus.PENDING_PROVIDER_RESPONSE,
        missing_documents=["itemized_bill.pdf"],
    )
    service = CaseService(JsonCaseRepository(tmp_path / "cases.json"))
    service.create_case(case)

    assert service.get_missing_information(case.case_id) == [
        "document:itemized_bill.pdf",
        "response:provider_response",
    ]


def test_get_deadline_risk_uses_supplied_current_date(tmp_path: Path) -> None:
    case = make_case(deadline=date(2026, 8, 15))
    service = CaseService(JsonCaseRepository(tmp_path / "cases.json"))
    service.create_case(case)

    result = service.get_deadline_risk(
        case.case_id,
        current_date=date(2026, 8, 10),
    )

    assert result.deadline == date(2026, 8, 15)
    assert result.days_remaining == 5
    assert result.risk is DeadlineRisk.MEDIUM


def test_submit_case_owns_creation_rules(tmp_path: Path) -> None:
    service = CaseService(
        JsonCaseRepository(tmp_path / "cases.json"),
        case_id_factory=lambda: "CASE-GENERATED",
    )

    case = service.submit_case(
        case_type=CaseType.IDR,
        provider_name="Synthetic Provider",
        created_date=date(2026, 8, 14),
        open_negotiation_start_date=date(2026, 8, 14),
        open_negotiation_end_date=date(2026, 8, 31),
        missing_documents=["itemized-bill.pdf"],
    )

    assert case.case_id == "CASE-GENERATED"
    assert case.status is CaseStatus.INCOMPLETE
    assert len(case.events) == 1
    assert case.events[0].type is CaseEventType.CASE_CREATED
    assert service.get_case(case.case_id) == case


def test_submit_case_does_not_overwrite_an_existing_reference(tmp_path: Path) -> None:
    service = CaseService(JsonCaseRepository(tmp_path / "cases.json"))
    service.create_case(make_case(case_id="CASE-EXISTS"))

    with pytest.raises(CaseAlreadyExistsError, match="CASE-EXISTS"):
        service.submit_case(
            case_id="CASE-EXISTS",
            case_type=CaseType.ONR,
            provider_name="Synthetic Provider",
            created_date=date(2026, 8, 14),
            open_negotiation_start_date=date(2026, 8, 14),
            open_negotiation_end_date=date(2026, 8, 31),
        )


def test_attach_document_adds_metadata_and_authoritative_event(tmp_path: Path) -> None:
    service = CaseService(JsonCaseRepository(tmp_path / "cases.json"))
    service.create_case(make_case(case_id="CASE-DOCUMENT"))
    document = Document(
        document_id="DOC-1",
        file_name="notice.pdf",
        s3_key="cases/CASE-DOCUMENT/DOC-1/notice.pdf",
    )

    updated = service.attach_document(
        "CASE-DOCUMENT",
        document,
        received_date=date(2026, 8, 14),
    )

    assert updated.documents == [document]
    assert updated.events[-1].type is CaseEventType.DOCUMENT_RECEIVED
    assert service.get_case("CASE-DOCUMENT") == updated
