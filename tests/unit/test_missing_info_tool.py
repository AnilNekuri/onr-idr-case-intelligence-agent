"""Expected examples for deterministic missing-information rules."""

import pytest

from app.models import CaseStatus
from app.tools.case_tool import CaseNotFoundError
from app.tools.missing_info_tool import get_missing_information
from tests.unit.tool_support import StubCaseRepository, make_case


def test_reports_each_declared_missing_document() -> None:
    case = make_case(
        status=CaseStatus.INCOMPLETE,
        missing_documents=["itemized_bill.pdf", "negotiation_notice.pdf"],
    )

    result = get_missing_information(StubCaseRepository(case), case.case_id)

    assert result == [
        "document:itemized_bill.pdf",
        "document:negotiation_notice.pdf",
    ]


def test_reports_pending_provider_response() -> None:
    case = make_case(
        status=CaseStatus.PENDING_PROVIDER_RESPONSE,
        provider_response_received=False,
    )

    result = get_missing_information(StubCaseRepository(case), case.case_id)

    assert result == ["response:provider_response"]


def test_does_not_report_response_when_it_was_received() -> None:
    case = make_case(
        status=CaseStatus.PENDING_PROVIDER_RESPONSE,
        provider_response_received=True,
    )

    assert get_missing_information(StubCaseRepository(case), case.case_id) == []


def test_complete_case_has_no_missing_information() -> None:
    case = make_case(status=CaseStatus.COMPLETE)

    assert get_missing_information(StubCaseRepository(case), case.case_id) == []


def test_missing_information_rejects_unknown_case() -> None:
    with pytest.raises(CaseNotFoundError, match="CASE-9999"):
        get_missing_information(StubCaseRepository(), "CASE-9999")
