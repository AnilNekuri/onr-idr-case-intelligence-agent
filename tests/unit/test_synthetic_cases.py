"""Phase checkpoint tests for the five deterministic synthetic cases."""

from datetime import date
from pathlib import Path

import pytest

from app.models import CaseStatus
from app.repositories import JsonCaseRepository
from app.services import CaseService
from app.tools import DeadlineRisk

CASES_FILE = Path(__file__).parents[2] / "data" / "cases.json"
CURRENT_DATE = date(2026, 8, 10)


@pytest.fixture
def service() -> CaseService:
    return CaseService(JsonCaseRepository(CASES_FILE))


@pytest.mark.parametrize(
    ("case_id", "expected_status"),
    [
        ("CASE-1001", CaseStatus.PENDING_PROVIDER_RESPONSE),
        ("CASE-1002", CaseStatus.INCOMPLETE),
        ("CASE-1003", CaseStatus.IN_PROGRESS),
        ("CASE-1004", CaseStatus.IN_PROGRESS),
        ("CASE-1005", CaseStatus.COMPLETE),
    ],
)
def test_loads_each_synthetic_case(
    service: CaseService,
    case_id: str,
    expected_status: CaseStatus,
) -> None:
    case = service.get_case(case_id)

    assert case is not None
    assert case.status is expected_status


@pytest.mark.parametrize(
    "case_id",
    ["CASE-1001", "CASE-1002", "CASE-1003", "CASE-1004", "CASE-1005"],
)
def test_each_synthetic_timeline_is_sorted(
    service: CaseService,
    case_id: str,
) -> None:
    timeline = service.get_timeline(case_id)

    assert [event.date for event in timeline] == sorted(
        event.date for event in timeline
    )


@pytest.mark.parametrize(
    ("case_id", "expected_missing_information"),
    [
        ("CASE-1001", ["response:provider_response"]),
        ("CASE-1002", ["document:itemized_bill.pdf"]),
        ("CASE-1003", []),
        ("CASE-1004", []),
        ("CASE-1005", []),
    ],
)
def test_synthetic_missing_information(
    service: CaseService,
    case_id: str,
    expected_missing_information: list[str],
) -> None:
    assert service.get_missing_information(case_id) == expected_missing_information


@pytest.mark.parametrize(
    ("case_id", "expected_days", "expected_risk"),
    [
        ("CASE-1001", 21, DeadlineRisk.LOW),
        ("CASE-1002", 15, DeadlineRisk.LOW),
        ("CASE-1003", 3, DeadlineRisk.HIGH),
        ("CASE-1004", -1, DeadlineRisk.MISSED),
        ("CASE-1005", 10, DeadlineRisk.LOW),
    ],
)
def test_synthetic_deadline_results(
    service: CaseService,
    case_id: str,
    expected_days: int,
    expected_risk: DeadlineRisk,
) -> None:
    result = service.get_deadline_risk(case_id, current_date=CURRENT_DATE)

    assert result.days_remaining == expected_days
    assert result.risk is expected_risk
